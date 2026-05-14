import streamlit as st
import pandas as pd
import random
import plotly.graph_objects as go
import io
import requests
import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CEO Command Center", layout="wide", initial_sidebar_state="collapsed")

# --- YAPAY ZEKA BAĞLANTISI ---
AI_HAZIR = False
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        kullanilabilir_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                kullanilabilir_model = m.name
                break
        if kullanilabilir_model:
            model = genai.GenerativeModel(kullanilabilir_model)
            AI_HAZIR = True
    except: pass

# --- VERİTABANI BAĞLANTISI ---
def get_leaderboard():
    if "BIN_ID" not in st.secrets or "JSONBIN_KEY" not in st.secrets: return []
    url = f"https://api.jsonbin.io/v3/b/{st.secrets['BIN_ID']}"
    headers = {"X-Master-Key": st.secrets['JSONBIN_KEY']}
    try: return requests.get(url, headers=headers).json().get('record', [])
    except: return []

def update_leaderboard(yeni_skor):
    if "BIN_ID" not in st.secrets or "JSONBIN_KEY" not in st.secrets: return
    mevcut = get_leaderboard()
    mevcut.append(yeni_skor)
    mevcut = sorted(mevcut, key=lambda x: x['hisse'], reverse=True)[:10]
    url = f"https://api.jsonbin.io/v3/b/{st.secrets['BIN_ID']}"
    headers = {"X-Master-Key": st.secrets['JSONBIN_KEY'], "Content-Type": "application/json"}
    requests.put(url, json=mevcut, headers=headers)

# --- HAFIZA BAŞLATMA ---
if 'gs' not in st.session_state:
    st.session_state.gs = {
        'tur': 1, 'nakit': 5000, 'borc': 2000, 'itibar': 100, 'hisse': 50.0,
        'bitti': False, 'aktif_olay': None, 'son_haber': "Piyasalar yeni CEO'nun hamlelerini bekliyor...",
        'log': [], 'hist_nakit': [5000], 'hist_hisse': [50.0],
        'rozetler': [], 'cfo_mesaj': "", 'skor_gonderildi': False, 'en_dusuk_nakit': 5000,
        'animasyon_oynadi': False, 'ik_yonetici': None, 'mulakat_gosterilen': None
    }
    st.session_state.kullanilan_indisler = []

MAX_TUR = 10

# --- CSS TASARIMLARI ---
bg_color = "#3A0E0E" if st.session_state.gs['nakit'] < 0 else "#0B0E14"
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; transition: background-color 0.5s ease; color: #F8FAFC; }}
    [data-testid="stMetric"] {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; padding: 15px !important; border-radius: 12px; backdrop-filter: blur(10px); }}
    .ticker-wrap {{ width: 100%; overflow: hidden; background-color: #1E293B; padding-left: 100%; box-sizing: content-box; border-bottom: 2px solid #38BDF8; margin-bottom: 20px; }}
    .ticker {{ display: inline-block; white-space: nowrap; padding-right: 100%; box-sizing: content-box; animation-iteration-count: infinite; animation-timing-function: linear; animation-name: ticker; animation-duration: 20s; }}
    .ticker__item {{ display: inline-block; padding: 10px 2rem; font-size: 1.1rem; color: #E2E8F0; font-weight: bold; }}
    @keyframes ticker {{ 0% {{ transform: translate3d(0, 0, 0); }} 100% {{ transform: translate3d(-100%, 0, 0); }} }}
    
    .badge-container {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; padding: 20px; }}
    .badge-card-premium {{ width: 200px; padding: 20px; border-radius: 15px; text-align: center; transition: transform 0.3s ease; position: relative; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }}
    .badge-card-premium:hover {{ transform: translateY(-10px); }}
    .tier-danger {{ background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%); box-shadow: 0 5px 15px rgba(220, 38, 38, 0.4); border: 1px solid #ef4444; color: white; }}
    .tier-average {{ background: linear-gradient(135deg, #4b5563 0%, #374151 100%); box-shadow: 0 5px 15px rgba(107, 114, 128, 0.3); border: 1px solid #9ca3af; }}
    .tier-bronze {{ background: linear-gradient(135deg, #3d2b1f 0%, #8c593b 100%); border: 1px solid #cd7f32; }}
    .tier-silver {{ background: linear-gradient(135deg, #2c3e50 0%, #bdc3c7 100%); border: 1px solid silver; }}
    .tier-gold {{ background: linear-gradient(135deg, #b8860b 0%, #ffd700 100%); border: 1px solid #ffd700; color: #000; }}
    .tier-platinum {{ background: linear-gradient(135deg, #1e3a8a 0%, #38bdf8 100%); border: 1px solid #e2e8f0; }}
    .tier-secret {{ background: linear-gradient(135deg, #4c1d95 0%, #c026d3 100%); border: 1px solid #f472b6; animation: pulse 2s infinite; }}
    
    .game-card {{ background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border: 2px solid #38BDF8; border-radius: 20px; padding: 40px; text-align: center; box-shadow: 0 15px 35px rgba(56, 189, 248, 0.15); margin: 10px auto; max-width: 800px; }}
    .card-title {{ color: #38BDF8; font-size: 32px; font-weight: 800; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }}
    .card-text {{ color: #F8FAFC; font-size: 20px; line-height: 1.6; font-weight: 400; }}
    .hire-card {{ background: rgba(30, 41, 59, 0.8); border: 1px solid #475569; padding: 20px; border-radius: 15px; margin-bottom: 15px; }}
    </style>
    """, unsafe_allow_html=True)

ticker_html = f"""<div class="ticker-wrap"><div class="ticker"><div class="ticker__item">📰 FLAŞ HABER: {st.session_state.gs['son_haber']}</div><div class="ticker__item">📊 BİST 100 Durumu: Hisse {st.session_state.gs['hisse']} ₺ seviyesinde.</div></div></div>"""
st.markdown(ticker_html, unsafe_allow_html=True)

# --- SENARYOLAR ---
def get_olaylar():
    return [
        {"baş": "📉 BIST 100 Sürü Psikolojisi!", "det": "Piyasada panik satışı başladı.", "sec": [("Hisse Geri Al (-1500₺)", -1500, 0, 10, 15), ("Sessiz Kal", 0, 0, -20, -15)]},
        {"baş": "🔄 Kripto vs Borsa", "det": "Yatırımcılar piyasadan çıkıp Bitcoin'e yöneliyor.", "sec": [("Kripto Fonu Kur (-2000₺)", -2000, 0, 20, 25), ("Temettü Dağıt (-3000₺)", -3000, 0, 40, 10)]},
        {"baş": "🏛️ Keynesyen Makro Şok!", "det": "Hükümet harcamaları artırdı ancak vergileri yükseltti.", "sec": [("Fiyatları Sabit Tut (-1000₺)", -1000, 0, 30, 5), ("Vergiyi Yansıt (+2000₺)", 2000, 0, -25, -10)]},
        {"baş": "⚠️ Analist Hatası", "det": "Ekonometrik modelde matematiksel işaret hatası tespit ettin.", "sec": [("Manuel Düzelt (-500₺)", -500, 0, 20, 5), ("Ekibi Değiştir (-1500₺)", -1500, 0, 40, 10)]},
        {"baş": "📈 Türev Piyasası", "det": "Kur riskinden korunmak için opsiyon alacak mısın?", "sec": [("Hedge Et (-2000₺)", -2000, 0, 30, 10), ("Açık Kal", 0, 0, -10, -15)]},
        {"baş": "🏭 Otomasyon Krizi", "det": "Veri setinin manuel elden geçirilmesi gerekiyor.", "sec": [("Sistemi Yenile (-2500₺)", -2500, 0, 10, 15), ("Manuel Çöz (-1000₺)", -1000, 0, -20, -5)]},
        {"baş": "🕵️ Global Danışmanlık", "det": "Danışmanlar agresif büyüme planı sunuyor.", "sec": [("İmzala (-3000₺)", -3000, 0, 50, 20), ("İç Kaynakla İlerle (+1000₺)", 1000, 0, 0, -5)]},
        {"baş": "💎 Yetenek Savaşı", "det": "Rakip şirket mühendislere %50 yüksek maaş teklif etti.", "sec": [("Maaşları Eşitle (-2000₺)", -2000, 0, 30, 5), ("Stajyer Al (+500₺)", 500, 0, -40, -15)]},
        {"baş": "🎤 Sokak Kültürü", "det": "Rap sanatçısına sponsor olma fırsatı.", "sec": [("Sponsor Ol (-1500₺)", -1500, 0, 45, 10), ("Geleneksel Reklam (-500₺)", -500, 0, 5, 0)]},
        {"baş": "🏗️ MEGA YATIRIM: Tesis", "det": "Kapasite artırımı. NPV pozitif.", "sec": [("Onayla (-4000₺)", -4000, 2000, 40, 15), ("Reddet (0₺)", 0, 0, 0, -2)]}
    ]

def rozet_hesapla():
    rozetler = []
    gs = st.session_state.gs
    if gs['nakit'] < 0: rozetler.append(("KAPIDA KALDIN", "🚪", "Şirket iflas etti.", "tier-danger"))
    if gs['hisse'] <= 25: rozetler.append(("TAHTA KAPANDI", "📉", "Tarihi çöküş.", "tier-danger"))
    
    if not any(r[3] == "tier-danger" for r in rozetler):
        if gs['hisse'] >= 150: rozetler.append(("PLATIN BORSA KURDU", "📈", "Piyasayı domine ettin!", "tier-platinum"))
        elif gs['hisse'] >= 100: rozetler.append(("ALTIN BORSA KURDU", "🐂", "Boğa piyasasının yıldızı.", "tier-gold"))
        elif gs['hisse'] >= 75: rozetler.append(("GÜMÜŞ BORSA KURDU", "📊", "Stabil büyüme.", "tier-silver"))
        if gs['itibar'] >= 180: rozetler.append(("PLATIN VİZYONER", "🕊️", "Etik liderlik.", "tier-platinum"))
        elif gs['itibar'] >= 140: rozetler.append(("ALTIN LİDER", "🌟", "Kurumsal imaj zirvede.", "tier-gold"))
        if gs['nakit'] >= 15000: rozetler.append(("ALTIN HAZİNEDAR", "💰", "Nakit akışı durdurulamaz.", "tier-gold"))
        if gs['en_dusuk_nakit'] < -1000 and gs['nakit'] > 5000: rozetler.append(("ANKA KUŞU", "🔥", "İflasın eşiğinden dönüş!", "tier-secret"))
        if gs['nakit'] == 0: rozetler.append(("MİLİMETRİK HESAP", "🎯", "Kasada tam 0 TL bıraktın!", "tier-secret"))

    if len(rozetler) == 0: rozetler.append(("SIRADAN CEO", "👔", "Sıkıcı bir 10 çeyrek.", "tier-average"))
    return rozetler

if st.session_state.gs['nakit'] < -3000 or st.session_state.gs['itibar'] <= 0 or st.session_state.gs['tur'] > MAX_TUR:
    if not st.session_state.gs['bitti']: st.session_state.gs['rozetler'] = rozet_hesapla()
    st.session_state.gs['bitti'] = True

# --- ARAYÜZ ---
st.markdown("<h2 style='text-align: center; color: #38BDF8;'>💼 EXECUTIVE COMMAND CENTER V3.1</h2>", unsafe_allow_html=True)

# YENİ: OYUN REHBERİ (İlk turda otomatik açık gelir)
with st.expander("📖 CEO EL KİTABI: Oyuna Başlamadan Önce Oku", expanded=(st.session_state.gs['tur'] == 1)):
    st.markdown("""
    **Hoş Geldin Yönetim Kurulu Başkanı!**  
    Bu simülasyon, sıradan bir oyun değil; ekonometrik modellerin, sürü psikolojisinin ve kurumsal stratejinin test edildiği acımasız bir laboratuvardır.
    
    🎯 **Amacın:** 10 Çeyrek (Tur) boyunca piyasa krizlerini yöneterek **Hisse** değerini ve **İtibarını** maksimize etmek, aynı zamanda **Kasa**'yı eksiden korumaktır.
    
    🛠️ **Nasıl Oynanır?**
    1. **Kriz Yönetimi:** Her tur karşına piyasadaki panik satışları (herd behavior), NPV gerektiren mega yatırımlar veya Black-Scholes temelli riskler çıkar. Alacağın her kararın bir fırsat maliyeti vardır.
    2. **İnsan Kaynakları:** Oyunu tek başına bitiremezsin. Hemen *İnsan Kaynakları* sekmesine git, adaylara kriz anı soruları sor ve onların cevaplarını **STAR (Durum, Görev, Eylem, Sonuç)** metodolojisine göre analiz ederek en doğru yeteneği işe al. Seçtiğin kişinin özellikleri kararlarını doğrudan etkiler.
    3. **Yapay Zeka Destekli CFO:** Kararsız kaldığında sağ üstteki **CFO'ya Danış** butonunu kullan. Sana finansal verilere dayanan sert ama stratejik tavsiyeler verecektir.
    
    *Dikkat: Kasayı sıfırın altına düşürürsen iflas çanları çalmaya başlar. Stratejini kur ve adını Liderlik Tablosu'na yazdır!*
    """)

t_komuta, t_ik, t_analiz, t_liderlik, t_rozetler = st.tabs(["🚀 Komuta", "🤝 İnsan Kaynakları", "📊 Analiz", "🏆 Liderlik", "📇 Rozetler"])

with t_komuta:
    if st.session_state.gs['ik_yonetici']: st.info(f"👔 **Aktif COO:** {st.session_state.gs['ik_yonetici']} operasyonları yönetiyor.")
    else: st.warning("⚠️ Şirketin bir COO'su yok! 'İnsan Kaynakları' sekmesinden hemen bir yönetici işe almalısın.")

    col_met_1, col_met_2 = st.columns([4, 1])
    with col_met_1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kasa (₺)", int(st.session_state.gs['nakit']))
        c2.metric("Borç (₺)", st.session_state.gs['borc'])
        c3.metric("İtibar", st.session_state.gs['itibar'])
        c4.metric("Hisse (₺)", round(st.session_state.gs['hisse'], 2))
    
    with col_met_2:
        btn_text = "🤖 CFO'ya Danış" if AI_HAZIR else "🤖 CFO (Yok)"
        if st.button(btn_text, disabled=not AI_HAZIR, use_container_width=True):
            with st.spinner("CFO analiz yapıyor..."):
                olay = st.session_state.gs['aktif_olay']
                if olay:
                    try: st.session_state.gs['cfo_mesaj'] = model.generate_content(f"Sen agresif CFO'sun. Kasa {st.session_state.gs['nakit']} TL. Kriz: '{olay['baş']}'. Seçenekler: 1){olay['sec'][0][0]} 2){olay['sec'][1][0]}. Kısaca hangisini seçmeliyiz?").text
                    except: st.session_state.gs['cfo_mesaj'] = "Hata: CFO'ya ulaşılamıyor."
    
    st.divider()

    if st.session_state.gs['bitti']:
        if not st.session_state.gs['animasyon_oynadi']:
            r_str = " ".join([r[0] for r in st.session_state.gs['rozetler']])
            if "PLATIN" in r_str or "ALTIN" in r_str: st.balloons()
            elif "ANKA" in r_str or "MİLİMETRİK" in r_str: st.snow()
            st.session_state.gs['animasyon_oynadi'] = True

        st.error("🏁 Simülasyon Sona Erdi!")
        st.markdown('<div class="badge-container">', unsafe_allow_html=True)
        for isim, icon, desc, tier in st.session_state.gs['rozetler']:
            st.markdown(f'<div class="badge-card-premium {tier}"><span class="badge-icon-lg">{icon}</span><div class="badge-name">{isim}</div><div class="badge-desc">{desc}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if not st.session_state.gs['skor_gonderildi']:
            oyuncu_adi = st.text_input("Şirketinin Adı (Maks 15 Karakter):", max_chars=15)
            if st.button("Skorumu Gönder", use_container_width=True, type="primary"):
                if oyuncu_adi:
                    update_leaderboard({"isim": oyuncu_adi, "hisse": st.session_state.gs['hisse'], "itibar": st.session_state.gs['itibar'], "rozet": st.session_state.gs['rozetler'][0][0]})
                    st.session_state.gs['skor_gonderildi'] = True
                    st.rerun()
        if st.button("🔄 Yeni Simülasyon", use_container_width=True): del st.session_state.gs; st.rerun()
    else:
        if st.session_state.gs['nakit'] < 0: st.toast("🚨 Kasa ekside! İflas riski!", icon="📉")

        if st.session_state.gs['aktif_olay'] is None:
            havuz = get_olaylar()
            if len(st.session_state.kullanilan_indisler) >= len(havuz): st.session_state.kullanilan_indisler = [] 
            idx = random.choice([i for i in range(len(havuz)) if i not in st.session_state.kullanilan_indisler])
            st.session_state.kullanilan_indisler.append(idx)
            st.session_state.gs['aktif_olay'] = havuz[idx]
            st.session_state.gs['cfo_mesaj'] = ""

        aktif = st.session_state.gs['aktif_olay']
        st.markdown(f"<div class='game-card'><div class='card-title'>{aktif['baş']}</div><div class='card-text'>{aktif['det']}</div></div>", unsafe_allow_html=True)
        if st.session_state.gs['cfo_mesaj']: st.info(f"👔 **CFO:** {st.session_state.gs['cfo_mesaj']}")
        
        col_btn = st.columns(len(aktif['sec']))
        for i, (isim, n, b, it, h) in enumerate(aktif['sec']):
            if col_btn[i].button(isim, use_container_width=True, key=f"btn_{st.session_state.gs['tur']}_{i}"):
                carpan_nakit = 1.0; carpan_hisse = 1.0
                if st.session_state.gs['ik_yonetici'] == "Zeynep": carpan_nakit = 0.9
                elif st.session_state.gs['ik_yonetici'] == "Cem": carpan_hisse = 1.5
                elif st.session_state.gs['ik_yonetici'] == "Ali": it += 5
                
                st.session_state.gs['nakit'] += (n * carpan_nakit if n < 0 else n)
                st.session_state.gs['borc'] += b; st.session_state.gs['itibar'] += it
                if st.session_state.gs['nakit'] < st.session_state.gs['en_dusuk_nakit']: st.session_state.gs['en_dusuk_nakit'] = st.session_state.gs['nakit']
                st.session_state.gs['hisse'] = max(5.0, round(st.session_state.gs['hisse'] + (h * carpan_hisse) + random.uniform(-2.0, 3.0) + (it*0.5), 2))
                st.session_state.gs['son_haber'] = f"Yönetim kararını verdi!"
                st.session_state.gs['log'].append({"Tur": st.session_state.gs['tur'], "Olay": aktif['baş'], "Nakit": st.session_state.gs['nakit']})
                st.session_state.gs['tur'] += 1; st.session_state.gs['aktif_olay'] = None; st.session_state.gs['cfo_mesaj'] = ""
                st.rerun()

with t_ik:
    st.write("### 🤝 Yönetici Mülakatları")
    if st.session_state.gs['ik_yonetici'] is None:
        st.markdown("Kararların maliyetini düşürmek ve verimi artırmak için bir **COO** seçmelisin. Adaylara soru sor ve cevaplarını **STAR** formatına göre analiz et.")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='hire-card'><h4>👩‍💼 Zeynep</h4><p><b>Ekol:</b> Kurumsal Denetim</p><p><b>Etkisi:</b> Olay maliyetlerini %10 düşürür.</p></div>", unsafe_allow_html=True)
            if st.button("Soru Sor", key="s_z"): st.session_state.gs['mulakat_gosterilen'] = 'Zeynep'
            if st.button("İşe Al", type="primary", key="a_z"): st.session_state.gs['ik_yonetici'] = "Zeynep"; st.rerun()
        with c2:
            st.markdown("<div class='hire-card'><h4>👨‍💼 Cem</h4><p><b>Ekol:</b> Wall Street</p><p><b>Etkisi:</b> Hisse kazançlarını x1.5 katlar.</p></div>", unsafe_allow_html=True)
            if st.button("Soru Sor", key="s_c"): st.session_state.gs['mulakat_gosterilen'] = 'Cem'
            if st.button("İşe Al", type="primary", key="a_c"): st.session_state.gs['ik_yonetici'] = "Cem"; st.rerun()
        with c3:
            st.markdown("<div class='hire-card'><h4>👨‍🎓 Ali</h4><p><b>Ekol:</b> Ekonometri</p><p><b>Etkisi:</b> Her tur +5 İtibar kalkanı sağlar.</p></div>", unsafe_allow_html=True)
            if st.button("Soru Sor", key="s_a"): st.session_state.gs['mulakat_gosterilen'] = 'Ali'
            if st.button("İşe Al", type="primary", key="a_a"): st.session_state.gs['ik_yonetici'] = "Ali"; st.rerun()

        st.write("---")
        if st.session_state.gs['mulakat_gosterilen'] == 'Zeynep':
            st.success("🗣️ **Zeynep:** \n**(S-Durum):** Nakit rezervleri tükenmişti.\n**(T-Görev):** CFO acil kurtarma planı istedi.\n**(A-Eylem):** Harcamaları %15 kestim.\n**(R-Sonuç):** 3 ayda nakit pozitif duruma geçtik.")
            st.caption("💡 *Not: Kusursuz bir STAR örneği.*")
        elif st.session_state.gs['mulakat_gosterilen'] == 'Cem':
            st.warning("🗣️ **Cem:** \nGeçen yıl piyasa çökerken türev piyasalarda açığa sattım ve 5 milyon dolar kazandırdım. Sonuca bakarım.")
            st.caption("💡 *Not: Sadece Sonuç (R) odaklı. Agresif.*")
        elif st.session_state.gs['mulakat_gosterilen'] == 'Ali':
            st.info("🗣️ **Ali:** \n**(S):** Modelde kriz sinyali vardı.\n**(T):** Lineer piyasa modelinde işaret hatası tespit ettim.\n**(A):** Hatayı denklem üzerinde düzelttim...\n*(Sonuca gelemedi)*")
            st.caption("💡 *Not: Analitik ama Sonuç (R) eksik.*")
    else: st.success(f"🎉 **{st.session_state.gs['ik_yonetici']}** şu an COO olarak görev yapıyor!")

with t_analiz: st.write("### 🧭 Şirket Sağlık Göstergeleri"); col_g1, col_g2 = st.columns(2); col_g1.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=st.session_state.gs['itibar'], title={'text':"İtibar", 'font':{'color':'white'}}, gauge={'axis':{'range':[0,200]},'bar':{'color':"#38BDF8"}})).update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300), use_container_width=True); col_g2.plotly_chart(go.Figure(go.Indicator(mode="gauge+number+delta", value=st.session_state.gs['hisse'], delta={'reference':50.0}, title={'text':"Hisse", 'font':{'color':'white'}}, gauge={'axis':{'range':[0,150]},'bar':{'color':"#A78BFA"}})).update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300), use_container_width=True)
with t_liderlik: 
    st.write("### 🌍 Global Top 10 CEO")
    tablo = get_leaderboard()
    if tablo: df_lb = pd.DataFrame(tablo); df_lb.index = df_lb.index + 1; st.dataframe(df_lb.rename(columns={"isim": "CEO", "hisse": "Hisse", "itibar": "İtibar", "rozet": "Unvan"}), use_container_width=True)
with t_rozetler: st.write("### 📜 Tüm Rozetler ve Gereksinimler"); st.markdown("- **🚨 UTANÇ ROZETLERİ:** Kasa eksiye düşerse alırsın.\n- **Platin Seviye:** Hisse > 150₺ veya İtibar > 180.\n- **Altın Seviye:** Hisse > 100₺ veya Nakit > 15.000₺.")
