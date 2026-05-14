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

# --- VERİTABANI BAĞLANTISI (LİDERLİK) ---
def get_leaderboard():
    if "BIN_ID" not in st.secrets or "JSONBIN_KEY" not in st.secrets: return []
    url = f"https://api.jsonbin.io/v3/b/{st.secrets['BIN_ID']}"
    headers = {"X-Master-Key": st.secrets['JSONBIN_KEY']}
    try:
        req = requests.get(url, headers=headers)
        return req.json().get('record', [])
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
        'rozetler': [], 'cfo_mesaj': "", 'skor_gonderildi': False, 'en_dusuk_nakit': 5000
    }
    st.session_state.kullanilan_indisler = []

MAX_TUR = 10

# --- CSS (ROZET VE KART TASARIMLARI) ---
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
    .tier-bronze {{ background: linear-gradient(135deg, #3d2b1f 0%, #8c593b 100%); box-shadow: 0 5px 15px rgba(140, 89, 59, 0.3); border: 1px solid #cd7f32; }}
    .tier-silver {{ background: linear-gradient(135deg, #2c3e50 0%, #bdc3c7 100%); box-shadow: 0 5px 15px rgba(189, 195, 199, 0.3); border: 1px solid silver; }}
    .tier-gold {{ background: linear-gradient(135deg, #b8860b 0%, #ffd700 100%); box-shadow: 0 5px 15px rgba(255, 215, 0, 0.3); border: 1px solid #ffd700; color: #000; }}
    .tier-platinum {{ background: linear-gradient(135deg, #1e3a8a 0%, #38bdf8 100%); box-shadow: 0 5px 20px rgba(56, 189, 248, 0.4); border: 1px solid #e2e8f0; }}
    .tier-secret {{ background: linear-gradient(135deg, #4c1d95 0%, #c026d3 100%); box-shadow: 0 5px 15px rgba(192, 38, 211, 0.5); border: 1px solid #f472b6; animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} 100% {{ opacity: 1; }} }}
    .badge-icon-lg {{ font-size: 50px; margin-bottom: 10px; display: block; }}
    .badge-name {{ font-weight: 900; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }}
    .badge-desc {{ font-size: 11px; margin-top: 8px; line-height: 1.2; opacity: 0.9; }}
    
    .game-card {{ background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border: 2px solid #38BDF8; border-radius: 20px; padding: 40px; text-align: center; box-shadow: 0 15px 35px rgba(56, 189, 248, 0.15); margin: 10px auto; max-width: 800px; }}
    .card-title {{ color: #38BDF8; font-size: 32px; font-weight: 800; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }}
    .card-text {{ color: #F8FAFC; font-size: 20px; line-height: 1.6; font-weight: 400; }}
    </style>
    """, unsafe_allow_html=True)

ticker_html = f"""<div class="ticker-wrap"><div class="ticker"><div class="ticker__item">📰 FLAŞ HABER: {st.session_state.gs['son_haber']}</div><div class="ticker__item">📊 BİST 100 Durumu: Hisse {st.session_state.gs['hisse']} ₺ seviyesinde.</div></div></div>"""
st.markdown(ticker_html, unsafe_allow_html=True)

# --- 15 TAM SENARYO HAVUZU (Çökme hatasını önler) ---
def get_olaylar():
    return [
        {"baş": "📉 BIST 100 Sürü Psikolojisi!", "det": "Piyasada panik satışı başladı. CSAD analizleri sürü psikolojisini gösteriyor.", "sec": [("Hisse Geri Al (-1500₺)", -1500, 0, 10, 15), ("Sessiz Kal", 0, 0, -20, -15)]},
        {"baş": "🔄 Kripto vs Borsa", "det": "Yatırımcılar piyasadan çıkıp Bitcoin'e yöneliyor.", "sec": [("Kripto Fonu Kur (-2000₺)", -2000, 0, 20, 25), ("Temettü Dağıt (-3000₺)", -3000, 0, 40, 10)]},
        {"baş": "🏛️ Keynesyen Makro Şok!", "det": "Hükümet harcamaları artırdı ancak vergileri de yükseltti.", "sec": [("Fiyatları Sabit Tut (-1000₺)", -1000, 0, 30, 5), ("Vergiyi Yansıt (+2000₺)", 2000, 0, -25, -10)]},
        {"baş": "⚠️ Analist Hatası", "det": "Ekonometrik modelde matematiksel işaret hatası tespit ettin.", "sec": [("Manuel Düzelt (-500₺)", -500, 0, 20, 5), ("Ekibi Değiştir (-1500₺)", -1500, 0, 40, 10)]},
        {"baş": "📈 Türev Piyasası", "det": "Kur riskinden korunmak için opsiyon alacak mısın?", "sec": [("Hedge Et (-2000₺)", -2000, 0, 30, 10), ("Açık Kal", 0, 0, -10, -15)]},
        {"baş": "🏭 Otomasyon Krizi", "det": "Veri setinin manuel elden geçirilmesi gerekiyor.", "sec": [("Sistemi Yenile (-2500₺)", -2500, 0, 10, 15), ("Manuel Çöz (-1000₺)", -1000, 0, -20, -5)]},
        {"baş": "🕵️ Global Danışmanlık", "det": "Danışmanlar agresif bir büyüme planı sunuyor.", "sec": [("İmzala (-3000₺)", -3000, 0, 50, 20), ("İç Kaynakla İlerle (+1000₺)", 1000, 0, 0, -5)]},
        {"baş": "💎 Yetenek Savaşı", "det": "Rakip şirket mühendislere %50 yüksek maaş teklif etti.", "sec": [("Maaşları Eşitle (-2000₺)", -2000, 0, 30, 5), ("Stajyer Al (+500₺)", 500, 0, -40, -15)]},
        {"baş": "🎤 Sokak Kültürü", "det": "Rap sanatçısına sponsor olma fırsatı.", "sec": [("Sponsor Ol (-1500₺)", -1500, 0, 45, 10), ("Geleneksel Reklam (-500₺)", -500, 0, 5, 0)]},
        {"baş": "📢 Rakip Karalama", "det": "En büyük rakibin ürünlerin hakkında PR kampanyası yürütüyor.", "sec": [("Karşı Kampanya (-2000₺)", -2000, 0, 20, 30), ("Hukuki Süreç (-1000₺)", -1000, 0, 10, 5)]},
        {"baş": "🏗️ MEGA YATIRIM: Tesis", "det": "Kapasite artırımı. NPV pozitif, IRR sınırda.", "sec": [("Onayla (-4000₺)", -4000, 2000, 40, 15), ("Reddet (0₺)", 0, 0, 0, -2)]},
        {"baş": "🌍 MEGA YATIRIM: Satın Alma", "det": "Avrupa'da rakibi satın alma fırsatı.", "sec": [("Satın Al (-5000₺)", -5000, 3000, 60, 25), ("Yerel Pazar (0₺)", 0, 0, -10, -5)]},
        {"baş": "🛡️ Siber Güvenlik İhlali", "det": "Şirket sunucularına saldırı düzenlendi.", "sec": [("Siber Şirket Tut (-2500₺)", -2500, 0, 40, 10), ("Sessizce Kapat (-500₺)", -500, 0, -50, -20)]},
        {"baş": "🌱 Yeşil Enerji", "det": "Karbon ayak izi yüksek şirketlere cezalar kesiliyor.", "sec": [("Güneş Paneli (-3000₺)", -3000, 0, 60, 15), ("Cezayı Kabul Et (-1500₺)", -1500, 0, -20, -10)]},
        {"baş": "🚢 Lojistik Tıkanıklığı", "det": "Küresel kriz nedeniyle tedarik zinciri koptu.", "sec": [("Uçak Kargo (-2000₺)", -2000, 0, 10, -5), ("Müşteri Beklesin (0₺)", 0, 0, -40, -15)]}
    ]

# --- ROZET MANTIĞI ---
def rozet_hesapla():
    rozetler = []
    gs = st.session_state.gs
    if gs['hisse'] >= 150: rozetler.append(("PLATIN BORSA KURDU", "📈", "Hisse fiyatında piyasayı domine ettin!", "tier-platinum"))
    elif gs['hisse'] >= 100: rozetler.append(("ALTIN BORSA KURDU", "📉", "Yatırımcıların yeni favorisi sensin.", "tier-gold"))
    elif gs['hisse'] >= 75: rozetler.append(("GÜMÜŞ BORSA KURDU", "📊", "Ortalamanın üzerinde bir büyüme.", "tier-silver"))

    if gs['itibar'] >= 180: rozetler.append(("PLATIN VİZYONER", "🕊️", "Dünya çapında etik bir liderlik sergiledin.", "tier-platinum"))
    elif gs['itibar'] >= 140: rozetler.append(("ALTIN LİDER", "🌟", "Kurumsal imajın zirvelerde.", "tier-gold"))

    if gs['nakit'] >= 15000: rozetler.append(("ALTIN HAZİNEDAR", "💰", "Şirketin nakit akışı durdurulamaz.", "tier-gold"))

    if gs['en_dusuk_nakit'] < -1000 and gs['nakit'] > 5000: rozetler.append(("ANKA KUŞU", "🔥", "İflasın eşiğinden muazzam bir dönüş yaptın!", "tier-secret"))
    if gs['nakit'] == 0: rozetler.append(("MILIMETRIK HESAP", "🎯", "Kasada tam 0 TL bırakarak bitirdin!", "tier-secret"))

    if not rozetler: rozetler.append(("BRONZ CEO", "💼", "Standart bir yönetim dönemi.", "tier-bronze"))
    return rozetler

if st.session_state.gs['nakit'] < -3000 or st.session_state.gs['itibar'] <= 0 or st.session_state.gs['tur'] > MAX_TUR:
    if not st.session_state.gs['bitti']:
        st.session_state.gs['rozetler'] = rozet_hesapla()
    st.session_state.gs['bitti'] = True

# --- ARAYÜZ ---
st.markdown("<h2 style='text-align: center; color: #38BDF8;'>💼 EXECUTIVE COMMAND CENTER V2.1</h2>", unsafe_allow_html=True)
t_komuta, t_analiz, t_liderlik, t_rozetler, t_arsiv = st.tabs(["🚀 Komuta", "📊 Analiz", "🏆 Liderlik", "📇 Rozet Galerisi", "📜 Şirket Arşivi"])

with t_komuta:
    col_met_1, col_met_2 = st.columns([4, 1])
    with col_met_1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kasa (₺)", st.session_state.gs['nakit'])
        c2.metric("Borç (₺)", st.session_state.gs['borc'])
        c3.metric("İtibar", st.session_state.gs['itibar'])
        c4.metric("Hisse (₺)", st.session_state.gs['hisse'])
    
    # AI CFO GERİ DÖNDÜ!
    with col_met_2:
        btn_text = "🤖 CFO'ya Danış" if AI_HAZIR else "🤖 CFO (Bağlantı Yok)"
        if st.button(btn_text, disabled=not AI_HAZIR, use_container_width=True):
            with st.spinner("CFO analiz yapıyor..."):
                olay = st.session_state.gs['aktif_olay']
                if olay:
                    prompt = f"Sen acımasız ve zeki bir Wall Street CFO'susun. Kasada {st.session_state.gs['nakit']} TL, Borç {st.session_state.gs['borc']} TL, İtibar {st.session_state.gs['itibar']}. Kriz: '{olay['baş']} - {olay['det']}'. Seçenekler: 1) {olay['sec'][0][0]} 2) {olay['sec'][1][0]}. CEO'ya agresif ve 3 cümlelik kısa bir tavsiye ver."
                    try:
                        st.session_state.gs['cfo_mesaj'] = model.generate_content(prompt).text
                    except Exception as e:
                        st.session_state.gs['cfo_mesaj'] = "Hata: CFO'ya ulaşılamıyor."
    
    st.divider()

    if st.session_state.gs['bitti']:
        st.error("🏁 Simülasyon Sona Erdi!")
        st.write("### 🏆 Kazanılan Başarılar")
        st.markdown('<div class="badge-container">', unsafe_allow_html=True)
        for isim, icon, desc, tier in st.session_state.gs['rozetler']:
            st.markdown(f'<div class="badge-card-premium {tier}"><span class="badge-icon-lg">{icon}</span><div class="badge-name">{isim}</div><div class="badge-desc">{desc}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SKOR GÖNDERME EKRANI GERİ DÖNDÜ!
        st.write("---")
        if not st.session_state.gs['skor_gonderildi']:
            st.write("### 🌍 Adını Tarihe Yazdır!")
            col_isim, col_btn_gonder = st.columns([3, 1])
            with col_isim: oyuncu_adi = st.text_input("Şirketinin Adı (Maks 15 Karakter):", max_chars=15)
            with col_btn_gonder:
                st.write(""); st.write("")
                if st.button("Skorumu Gönder", use_container_width=True, type="primary"):
                    if oyuncu_adi:
                        with st.spinner("Skor yükleniyor..."):
                            rozet_isim = st.session_state.gs['rozetler'][0][0] if st.session_state.gs['rozetler'] else "Yönetici"
                            update_leaderboard({"isim": oyuncu_adi, "hisse": st.session_state.gs['hisse'], "itibar": st.session_state.gs['itibar'], "rozet": rozet_isim})
                            st.session_state.gs['skor_gonderildi'] = True
                            st.rerun()
                    else: st.warning("Lütfen ismini gir!")
        else: st.success("Skorun buluta kaydedildi! 'Liderlik' sekmesinden bakabilirsin.")

        st.write("---")
        if st.button("🔄 Yeni Simülasyon Başlat", use_container_width=True):
            del st.session_state.gs
            st.rerun()
    else:
        if st.session_state.gs['aktif_olay'] is None:
            havuz = get_olaylar()
            if len(st.session_state.kullanilan_indisler) >= len(havuz): st.session_state.kullanilan_indisler = [] # Hata Koruması
            idx = random.choice([i for i in range(len(havuz)) if i not in st.session_state.kullanilan_indisler])
            st.session_state.kullanilan_indisler.append(idx)
            st.session_state.gs['aktif_olay'] = havuz[idx]
            st.session_state.gs['cfo_mesaj'] = ""

        aktif = st.session_state.gs['aktif_olay']
        st.markdown(f"<div class='game-card'><div class='card-title'>{aktif['baş']}</div><div class='card-text'>{aktif['det']}</div></div>", unsafe_allow_html=True)
        
        if st.session_state.gs['cfo_mesaj']:
            st.info(f"👔 **Yapay Zeka CFO Diyor ki:** {st.session_state.gs['cfo_mesaj']}")
        
        col_btn = st.columns(len(aktif['sec']))
        for i, (isim, n, b, it, h) in enumerate(aktif['sec']):
            if col_btn[i].button(isim, use_container_width=True, key=f"btn_{st.session_state.gs['tur']}_{i}"):
                st.session_state.gs['nakit'] += n; st.session_state.gs['borc'] += b; st.session_state.gs['itibar'] += it
                if st.session_state.gs['nakit'] < st.session_state.gs['en_dusuk_nakit']: st.session_state.gs['en_dusuk_nakit'] = st.session_state.gs['nakit']
                
                volatilite = random.uniform(-2.0, 3.0)
                st.session_state.gs['hisse'] = max(5.0, round(st.session_state.gs['hisse'] + h + volatilite + (it*0.5), 2))
                st.session_state.gs['son_haber'] = f"Yönetim '{aktif['baş']}' kararını verdi!"
                st.session_state.gs['log'].append({"Tur": st.session_state.gs['tur'], "Olay": aktif['baş'], "Nakit": st.session_state.gs['nakit'], "Hisse": st.session_state.gs['hisse']})
                st.session_state.gs['tur'] += 1
                st.session_state.gs['hist_nakit'].append(st.session_state.gs['nakit'])
                st.session_state.gs['hist_hisse'].append(st.session_state.gs['hisse'])
                st.session_state.gs['aktif_olay'] = None
                st.session_state.gs['cfo_mesaj'] = ""
                st.rerun()

with t_analiz:
    st.write("### 🧭 Şirket Sağlık Göstergeleri")
    col_g1, col_g2 = st.columns(2)
    with col_g1: st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=st.session_state.gs['itibar'], title={'text':"İtibar", 'font':{'color':'white'}}, gauge={'axis':{'range':[0,200]},'bar':{'color':"#38BDF8"}})).update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300), use_container_width=True)
    with col_g2: st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number+delta", value=st.session_state.gs['hisse'], delta={'reference':50.0}, title={'text':"Hisse", 'font':{'color':'white'}}, gauge={'axis':{'range':[0,150]},'bar':{'color':"#A78BFA"}})).update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300), use_container_width=True)

with t_liderlik:
    st.write("### 🌍 Global Top 10 CEO")
    if "BIN_ID" in st.secrets:
        tablo = get_leaderboard()
        if tablo:
            df_lb = pd.DataFrame(tablo)
            df_lb.index = df_lb.index + 1
            df_lb = df_lb.rename(columns={"isim": "CEO / Şirket", "hisse": "Hisse Değeri (₺)", "itibar": "İtibar Puanı", "rozet": "Kazanılan Unvan"})
            st.dataframe(df_lb, use_container_width=True)
        else: st.info("Henüz kimse skor göndermedi. Piyasalar ilk efsane CEO'sunu bekliyor!")

with t_rozetler:
    st.write("### 📜 Tüm Rozetler ve Gereksinimler")
    st.markdown("""
    - **Platin Seviye:** Hisse > 150₺ veya İtibar > 180. (Zirve CEO)
    - **Altın Seviye:** Hisse > 100₺ veya Nakit > 15.000₺. (Usta Yönetici)
    - **Gümüş Seviye:** Hisse > 75₺. (Başarılı Yönetici)
    - **Gizli Rozetler:** Krizden muazzam bir dönüş yapmak veya kasayı kuruşu kuruşuna boşaltmak.
    """)

with t_arsiv:
    st.write("### 📜 Geçmiş Kararlar ve Finansal Akış")
    if len(st.session_state.gs['log']) > 0:
        st.dataframe(pd.DataFrame(st.session_state.gs['log']), use_container_width=True)
