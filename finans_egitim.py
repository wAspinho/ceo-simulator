import streamlit as st
import pandas as pd
import random
import plotly.graph_objects as go
import numpy_financial as npf
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CEO Command Center", layout="wide", initial_sidebar_state="collapsed")

# --- HAFIZA BAŞLATMA ---
if 'gs' not in st.session_state:
    st.session_state.gs = {
        'tur': 1, 'nakit': 5000, 'borc': 2000, 'itibar': 100, 'hisse': 50.0,
        'bitti': False, 'aktif_olay': None, 'son_haber': "Piyasalar yeni CEO'nun hamlelerini bekliyor...",
        'log': [], 'hist_nakit': [5000], 'hist_hisse': [50.0]
    }
    st.session_state.kullanilan_indisler = []

MAX_TUR = 10

# --- DİNAMİK CSS VE OYUN KARTI (GAME CARD) TASARIMI ---
bg_color = "#3A0E0E" if st.session_state.gs['nakit'] < 0 else "#0B0E14"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; transition: background-color 0.5s ease; color: #F8FAFC; }}
    
    [data-testid="stMetric"] {{
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        padding: 15px !important;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }}
    
    /* Kayan Haber Şeridi */
    .ticker-wrap {{
        width: 100%; overflow: hidden; background-color: #1E293B; 
        padding-left: 100%; box-sizing: content-box; border-bottom: 2px solid #38BDF8; margin-bottom: 20px;
    }}
    .ticker {{
        display: inline-block; white-space: nowrap; padding-right: 100%; box-sizing: content-box;
        animation-iteration-count: infinite; animation-timing-function: linear; animation-name: ticker; animation-duration: 20s;
    }}
    .ticker__item {{ display: inline-block; padding: 10px 2rem; font-size: 1.1rem; color: #E2E8F0; font-weight: bold; }}
    @keyframes ticker {{
        0% {{ transform: translate3d(0, 0, 0); }}
        100% {{ transform: translate3d(-100%, 0, 0); }}
    }}

    /* ANA OYUN KARTI CSS'İ */
    .game-card {{
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 2px solid #38BDF8;
        border-radius: 20px;
        padding: 50px 40px;
        text-align: center;
        box-shadow: 0 15px 35px rgba(56, 189, 248, 0.15);
        margin: 10px auto 30px auto;
        max-width: 700px;
        position: relative;
        overflow: hidden;
    }}
    .card-title {{ color: #38BDF8; font-size: 32px; font-weight: 800; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }}
    .card-text {{ color: #F8FAFC; font-size: 20px; line-height: 1.6; font-weight: 400; }}
    
    /* 3D FLIP CARD CSS */
    .flip-card {{
        background-color: transparent; width: 100%; height: 280px; perspective: 1000px; margin-bottom: 20px;
    }}
    .flip-card-inner {{
        position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border-radius: 15px;
    }}
    .flip-card:hover .flip-card-inner {{ transform: rotateY(180deg); }}
    .flip-card-front, .flip-card-back {{
        position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; border-radius: 15px; padding: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center;
    }}
    .flip-card-front {{ background: linear-gradient(145deg, #1e293b, #0f172a); color: #38BDF8; border: 1px solid #334155; }}
    .flip-card-front p {{ color: #94A3B8; font-size: 14px; margin-top: 10px; }}
    .flip-card-back {{ background: linear-gradient(145deg, #0284C7, #0369A1); color: white; transform: rotateY(180deg); border: 1px solid #38BDF8; }}
    .flip-card-back ul {{ text-align: left; font-size: 14px; list-style-type: none; padding: 0; }}
    .flip-card-back li {{ margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.2); }}
    </style>
    """, unsafe_allow_html=True)

ticker_html = f"""
<div class="ticker-wrap"><div class="ticker">
    <div class="ticker__item">📰 FLAŞ HABER: {st.session_state.gs['son_haber']}</div>
    <div class="ticker__item">📊 BİST 100 Durumu: Hisse {st.session_state.gs['hisse']} ₺ seviyesinde.</div>
</div></div>
"""
st.markdown(ticker_html, unsafe_allow_html=True)

def veri_indir_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Veri')
    return output.getvalue()

def hisse_guncelle(itibar_degisimi, secim_etkisi):
    volatilite = random.uniform(-2.0, 3.0)
    st.session_state.gs['hisse'] = max(5.0, round(st.session_state.gs['hisse'] + secim_etkisi + volatilite + (itibar_degisimi * 0.5), 2))

# --- DEV SENARYO HAVUZU ---
def get_olaylar():
    return [
        {"baş": "📉 BIST 100 Sürü Psikolojisi!", "det": "Piyasada panik satışı başladı. CSAD analizleri sürü psikolojisini gösteriyor.", "sec": [("Hisse Geri Al (-1500₺, +10 Hisse)", -1500, 0, 10, 15), ("Sessiz Kal (Düşüş Devam Eder)", 0, 0, -20, -15)]},
        {"baş": "🔄 Kripto vs Borsa Kayması", "det": "Yatırımcılar piyasadan çıkıp Bitcoin'e yöneliyor.", "sec": [("Kripto Fonu Kur (-2000₺, Riskli)", -2000, 0, 20, 25), ("Temettü Dağıt (-3000₺, Güvenli)", -3000, 0, 40, 10)]},
        {"baş": "🏛️ Keynesyen Makro Şok!", "det": "Hükümet harcamaları artırdı ancak vergileri de yükseltti. Tüketim dengesi değişiyor.", "sec": [("Fiyatları Sabit Tut (-1000₺)", -1000, 0, 30, 5), ("Vergiyi Yansıt (+2000₺, -25 İtibar)", 2000, 0, -25, -10)]},
        {"baş": "⚠️ Analist Hatası: İşaret Yanılgısı!", "det": "Ekonometrik modelde kritik bir matematiksel işaret hatası (+ yerine -) tespit ettin.", "sec": [("Manuel Düzelt (-500₺)", -500, 0, 20, 5), ("Ekibi Değiştir (-1500₺)", -1500, 0, 40, 10)]},
        {"baş": "📈 Türev Piyasası: Hedge Kararı", "det": "Kur riskinden korunmak için opsiyon alacak mısın? BSM modeline göre volatilite yüksek.", "sec": [("Hedge Et (-2000₺, Güvenli)", -2000, 0, 30, 10), ("Açık Kal (Riskli Seçim)", 0, 0, -10, -15)]},
        {"baş": "🏭 Fabrikada Otomasyon Krizi", "det": "Veri setinin manuel olarak elden geçirilmesi ve düzeltilmesi gerekiyor.", "sec": [("Sistemi Yenile (-2500₺)", -2500, 0, 10, 15), ("Manuel Çöz (-1000₺)", -1000, 0, -20, -5)]},
        {"baş": "🕵️ Global Danışmanlık", "det": "Danışmanlar (STAR) odaklı agresif bir büyüme planı sunuyor.", "sec": [("İmzala (-3000₺)", -3000, 0, 50, 20), ("İç Kaynakla İlerle (+1000₺)", 1000, 0, 0, -5)]},
        {"baş": "💎 Yetenek Savaşı", "det": "Rakip şirket mühendislere %50 daha yüksek maaş teklif etti.", "sec": [("Maaşları Eşitle (-2000₺)", -2000, 0, 30, 5), ("Stajyer Al (+500₺)", 500, 0, -40, -15)]},
        {"baş": "🎤 Sokak Kültürü Sponsorluğu", "det": "Sokak kültürü temalı sözler yazan bir rap sanatçısına sponsor olma fırsatı.", "sec": [("Kampanya Başlat (-1500₺)", -1500, 0, 45, 10), ("Geleneksel Reklam (-500₺)", -500, 0, 5, 0)]},
        {"baş": "📢 Rakip Karalama", "det": "En büyük rakibin ürünlerin hakkında PR kampanyası yürütüyor.", "sec": [("Karşı Kampanya (-2000₺)", -2000, 0, 20, 30), ("Hukuki Süreç (-1000₺)", -1000, 0, 10, 5)]},
        {"baş": "🏗️ MEGA YATIRIM: Yeni Tesis", "det": "Kapasite artırımı. NPV pozitif, IRR sınırda. İlk Yatırım: -4000₺", "sec": [("Onayla (-4000₺)", -4000, 2000, 40, 15), ("Reddet (Nakit Korunur)", 0, 0, 0, -2)]},
        {"baş": "🌍 MEGA YATIRIM: Satın Alma", "det": "Avrupa'da batan bir rakibi satın alma fırsatı. Başlangıç maliyeti: -5000₺.", "sec": [("Satın Al (-5000₺)", -5000, 3000, 60, 25), ("Yerel Pazarda Kal (0₺)", 0, 0, -10, -5)]},
        {"baş": "🛡️ Siber Güvenlik İhlali!", "det": "Şirket sunucularına saldırı düzenlendi.", "sec": [("Siber Şirket Tut (-2500₺)", -2500, 0, 40, 10), ("Sessizce Kapat (-500₺)", -500, 0, -50, -20)]},
        {"baş": "🌱 Yeşil Enerji", "det": "Hükümet karbon ayak izi yüksek şirketlere cezalar kesiyor.", "sec": [("Güneş Paneli (-3000₺)", -3000, 0, 60, 15), ("Cezayı Kabul Et (-1500₺)", -1500, 0, -20, -10)]},
        {"baş": "🚢 Lojistik Tıkanıklığı", "det": "Küresel kriz nedeniyle tedarik zinciri koptu.", "sec": [("Uçak Kargo (-2000₺)", -2000, 0, 10, -5), ("Müşteri Beklesin (0₺)", 0, 0, -40, -15)]}
    ]

if st.session_state.gs['nakit'] < -3000 or st.session_state.gs['itibar'] <= 0 or st.session_state.gs['tur'] > MAX_TUR:
    st.session_state.gs['bitti'] = True

st.markdown("<h2 style='text-align: center; color: #38BDF8;'>💼 EXECUTIVE COMMAND CENTER</h2>", unsafe_allow_html=True)

tab_komuta, tab_analiz, tab_tarihce, tab_flashcard = st.tabs(["🚀 Komuta Merkezi", "📊 Analiz Departmanı", "📜 Şirket Arşivi", "📇 Eğitim Kartları"])

# ==========================================
# SEKME 1: KOMUTA MERKEZİ 
# ==========================================
with tab_komuta:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kasa (₺)", st.session_state.gs['nakit'])
    c2.metric("Borç (₺)", st.session_state.gs['borc'])
    c3.metric("İtibar", st.session_state.gs['itibar'])
    c4.metric("Hisse (₺)", st.session_state.gs['hisse'])
    
    st.divider()

    if st.session_state.gs['bitti']:
        st.error("🏁 Simülasyon Sona Erdi!")
        if st.button("🔄 Yeni Simülasyon Başlat", use_container_width=True):
            del st.session_state.gs
            st.rerun()
    else:
        if st.session_state.gs['nakit'] < 0:
            st.error("🚨 DİKKAT: Şirket likidite krizinde! Acil nakit yaratacak kararlar alınmalı.")

        if st.session_state.gs['aktif_olay'] is None:
            havuz = get_olaylar()
            if len(st.session_state.kullanilan_indisler) >= len(havuz):
                st.session_state.kullanilan_indisler = []
            musait = [i for i in range(len(havuz)) if i not in st.session_state.kullanilan_indisler]
            idx = random.choice(musait)
            st.session_state.kullanilan_indisler.append(idx)
            st.session_state.gs['aktif_olay'] = havuz[idx]

        aktif = st.session_state.gs['aktif_olay']
        
        # --- MERKEZİ OYUN KARTI ---
        st.markdown(f"""
        <div class="game-card">
            <div class="card-title">{aktif['baş']}</div>
            <div class="card-text">{aktif['det']}</div>
        </div>
        """, unsafe_allow_html=True)

        if "MEGA YATIRIM" in aktif['baş']:
            st.warning("💡 Analist Notu: Projenin finansal fizibilitesini dikkate alın.")

        st.write("<h4 style='text-align:center;'>Stratejik Kararın Nedir?</h4>", unsafe_allow_html=True)
        col_btn = st.columns(len(aktif['sec']))
        for i, (isim, n, b, it, h) in enumerate(aktif['sec']):
            if col_btn[i].button(isim, use_container_width=True, key=f"btn_{st.session_state.gs['tur']}_{i}"):
                st.session_state.gs['nakit'] += n
                st.session_state.gs['borc'] += b
                st.session_state.gs['itibar'] += it
                hisse_guncelle(it, h)
                st.session_state.gs['son_haber'] = f"Yönetim '{aktif['baş']}' konusunda kararını verdi!"
                st.session_state.gs['log'].append({"Tur": st.session_state.gs['tur'], "Olay": aktif['baş'], "Karar": isim.split('(')[0], "Nakit": st.session_state.gs['nakit'], "Hisse": st.session_state.gs['hisse']})
                st.session_state.gs['tur'] += 1
                st.session_state.gs['hist_nakit'].append(st.session_state.gs['nakit'])
                st.session_state.gs['hist_hisse'].append(st.session_state.gs['hisse'])
                st.session_state.gs['aktif_olay'] = None
                st.rerun()

# ==========================================
# SEKME 2: ANALİZ DEPARTMANI
# ==========================================
with tab_analiz:
    st.write("### 🧭 Şirket Sağlık Göstergeleri")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_itibar = go.Figure(go.Indicator(mode = "gauge+number", value = st.session_state.gs['itibar'], title = {'text': "Kurumsal İtibar", 'font': {'color': 'white'}}, gauge = {'axis': {'range': [0, 200]}, 'bar': {'color': "#38BDF8"}}))
        fig_itibar.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300)
        st.plotly_chart(fig_itibar, use_container_width=True)
    with col_g2:
        fig_hisse = go.Figure(go.Indicator(mode = "gauge+number+delta", value = st.session_state.gs['hisse'], delta = {'reference': 50.0}, title = {'text': "BIST Hisse Fiyatı", 'font': {'color': 'white'}}, gauge = {'axis': {'range': [0, 150]}, 'bar': {'color': "#A78BFA"}}))
        fig_hisse.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300)
        st.plotly_chart(fig_hisse, use_container_width=True)
    st.write("### 📉 Finansal Akış Trendi")
    st.line_chart(pd.DataFrame({"Nakit": st.session_state.gs['hist_nakit']}), color="#38BDF8")

# ==========================================
# SEKME 3: ŞİRKET ARŞİVİ
# ==========================================
with tab_tarihce:
    st.write("### 📜 Geçmiş Kararlar ve Veri Kaydı")
    if len(st.session_state.gs['log']) > 0:
        df_log = pd.DataFrame(st.session_state.gs['log'])
        st.dataframe(df_log, use_container_width=True)
        st.download_button("📥 Tabloyu Excel Olarak İndir", data=veri_indir_excel(df_log), file_name='ceo_arşivi.xlsx')
    else:
        st.write("Henüz bir karar alınmadı.")

# ==========================================
# SEKME 4: FLASHCARDS (EĞİTİM KARTLARI)
# ==========================================
with tab_flashcard:
    st.write("### 🧠 Finansal Senaryo Eğitim Kartları")
    st.write("Aşağıdaki kartlar simülasyonda karşınıza çıkabilecek finansal teorileri içerir. Senaryoyu okuyun ve sonucu görmek için **farenizi kartın üzerine getirin** (Hover).")
    st.write("") 
    
    havuz = get_olaylar()
    cols = st.columns(3) 
    
    for i, olay in enumerate(havuz):
        secenekler_html = "".join([f"<li><b>{s[0]}</b> <br><small>Nakit: {s[1]}₺ | İtibar: {s[3]}</small></li>" for s in olay['sec']])
        card_html = f"""
        <div class="flip-card">
          <div class="flip-card-inner">
            <div class="flip-card-front">
              <h4 style="margin: 0; color: #38BDF8;">{olay['baş']}</h4>
              <p>{olay['det']}</p>
            </div>
            <div class="flip-card-back">
              <h5 style="margin-bottom: 10px;">Stratejik Etkiler:</h5>
              <ul>{secenekler_html}</ul>
            </div>
          </div>
        </div>
        """
        cols[i % 3].markdown(card_html, unsafe_allow_html=True)
