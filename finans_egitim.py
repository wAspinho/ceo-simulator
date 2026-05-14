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
    except:
        pass

# --- VERİTABANI BAĞLANTISI ---
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

# --- GELİŞMİŞ ROZET TASARIMI (CSS) ---
st.markdown("""
    <style>
    /* Genel Tema */
    .stApp { background-color: #0B0E14; color: #F8FAFC; }
    
    /* Rozet Kartları Tasarımı */
    .badge-container {
        display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; padding: 20px;
    }
    .badge-card-premium {
        width: 200px; padding: 20px; border-radius: 15px; text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative; overflow: hidden; border: 1px solid rgba(255,255,255,0.1);
    }
    .badge-card-premium:hover { transform: translateY(-10px); }
    
    /* Seviye Renkleri */
    .tier-bronze { background: linear-gradient(135deg, #3d2b1f 0%, #8c593b 100%); box-shadow: 0 5px 15px rgba(140, 89, 59, 0.3); border: 1px solid #cd7f32; }
    .tier-silver { background: linear-gradient(135deg, #2c3e50 0%, #bdc3c7 100%); box-shadow: 0 5px 15px rgba(189, 195, 199, 0.3); border: 1px solid #silver; }
    .tier-gold { background: linear-gradient(135deg, #b8860b 0%, #ffd700 100%); box-shadow: 0 5px 15px rgba(255, 215, 0, 0.3); border: 1px solid #ffd700; color: #000; }
    .tier-platinum { background: linear-gradient(135deg, #1e3a8a 0%, #38bdf8 100%); box-shadow: 0 5px 20px rgba(56, 189, 248, 0.4); border: 1px solid #e2e8f0; }
    .tier-secret { background: linear-gradient(135deg, #4c1d95 0%, #c026d3 100%); box-shadow: 0 5px 15px rgba(192, 38, 211, 0.5); border: 1px solid #f472b6; animation: pulse 2s infinite; }
    
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }

    .badge-icon-lg { font-size: 50px; margin-bottom: 10px; display: block; }
    .badge-name { font-weight: 900; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }
    .badge-desc { font-size: 11px; margin-top: 8px; line-height: 1.2; opacity: 0.9; }

    /* Oyun Kartı */
    .game-card {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border: 2px solid #38BDF8; border-radius: 20px; padding: 40px; text-align: center; box-shadow: 0 15px 35px rgba(56, 189, 248, 0.15); margin: 10px auto; max-width: 800px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SENARYOLAR ---
def get_olaylar():
    return [
        {"baş": "📉 BIST 100 Sürü Psikolojisi!", "det": "Piyasada panik satışı başladı. CSAD analizleri sürü psikolojisini gösteriyor.", "sec": [("Hisse Geri Al (-1500₺, +10 Hisse)", -1500, 0, 10, 15), ("Sessiz Kal (Düşüş)", 0, 0, -20, -15)]},
        {"baş": "🔄 Kripto vs Borsa", "det": "Yatırımcılar piyasadan çıkıp Bitcoin'e yöneliyor.", "sec": [("Kripto Fonu Kur (-2000₺, Riskli)", -2000, 0, 20, 25), ("Temettü Dağıt (-3000₺, Güvenli)", -3000, 0, 40, 10)]},
        {"baş": "🕵️ Global Danışmanlık", "det": "Danışmanlar agresif bir büyüme planı sunuyor.", "sec": [("İmzala (-3000₺)", -3000, 0, 50, 20), ("İç Kaynakla İlerle (+1000₺)", 1000, 0, 0, -5)]},
        {"baş": "🛡️ Siber Güvenlik İhlali", "det": "Şirket sunucularına saldırı düzenlendi.", "sec": [("Siber Şirket Tut (-2500₺)", -2500, 0, 40, 10), ("Sessizce Kapat (-500₺)", -500, 0, -50, -20)]},
        {"baş": "🌱 Yeşil Enerji", "det": "Karbon ayak izi yüksek şirketlere cezalar kesiliyor.", "sec": [("Güneş Paneli (-3000₺)", -3000, 0, 60, 15), ("Cezayı Kabul Et (-1500₺)", -1500, 0, -20, -10)]},
        {"baş": "🏗️ MEGA YATIRIM: Tesis", "det": "Kapasite artırımı. NPV pozitif. İlk Yatırım: -4000₺", "sec": [("Onayla (-4000₺)", -4000, 2000, 40, 15), ("Reddet (0₺)", 0, 0, 0, -2)]}
    ]

# --- OYUN SONU VE ROZET MANTIĞI ---
def rozet_hesapla():
    rozetler = []
    gs = st.session_state.gs
    
    # 1. Hisse Performansı (Borsa Kurdu Serisi)
    if gs['hisse'] >= 150: rozetler.append(("PLATIN BORSA KURDU", "📈", "Hisse fiyatında piyasayı domine ettin!", "tier-platinum"))
    elif gs['hisse'] >= 100: rozetler.append(("ALTIN BORSA KURDU", "📉", "Yatırımcıların yeni favorisi sensin.", "tier-gold"))
    elif gs['hisse'] >= 75: rozetler.append(("GÜMÜŞ BORSA KURDU", "📊", "Ortalamanın üzerinde bir büyüme.", "tier-silver"))

    # 2. İtibar Performansı (Halkın Kahramanı Serisi)
    if gs['itibar'] >= 180: rozetler.append(("PLATIN VİZYONER", "🕊️", "Dünya çapında etik bir liderlik sergiledin.", "tier-platinum"))
    elif gs['itibar'] >= 140: rozetler.append(("ALTIN LİDER", "🌟", "Kurumsal imajın zirvelerde.", "tier-gold"))

    # 3. Nakit Yönetimi (Finans Dehası)
    if gs['nakit'] >= 15000: rozetler.append(("ALTIN HAZİNEDAR", "💰", "Şirketin nakit akışı durdurulamaz.", "tier-gold"))

    # 4. GİZLİ ROZETLER (SECRET)
    if gs['en_dusuk_nakit'] < -1000 and gs['nakit'] > 5000:
        rozetler.append(("ANKA KUŞU", "🔥", "İflasın eşiğinden muazzam bir dönüş yaptın!", "tier-secret"))
    
    if gs['nakit'] == 0:
        rozetler.append(("MILIMETRIK HESAP", "🎯", "Kasada tam 0 TL bırakarak bitirdin!", "tier-secret"))

    if not rozetler:
        rozetler.append(("BRONZ CEO", "💼", "Standart bir yönetim dönemi.", "tier-bronze"))
        
    return rozetler

if st.session_state.gs['nakit'] < -3000 or st.session_state.gs['itibar'] <= 0 or st.session_state.gs['tur'] > MAX_TUR:
    if not st.session_state.gs['bitti']:
        st.session_state.gs['rozetler'] = rozet_hesapla()
    st.session_state.gs['bitti'] = True

# --- ARAYÜZ ---
st.markdown("<h2 style='text-align: center; color: #38BDF8;'>💼 EXECUTIVE COMMAND CENTER V2.0</h2>", unsafe_allow_html=True)
t1, t2, t3, t4 = st.tabs(["🚀 Komuta", "📊 Analiz", "🏆 Liderlik", "📇 Rozet Galerisi"])

with t1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kasa (₺)", st.session_state.gs['nakit'])
    c2.metric("Borç (₺)", st.session_state.gs['borc'])
    c3.metric("İtibar", st.session_state.gs['itibar'])
    c4.metric("Hisse (₺)", st.session_state.gs['hisse'])
    
    st.divider()

    if st.session_state.gs['bitti']:
        st.error("🏁 Simülasyon Sona Erdi!")
        
        # --- ROZET GÖSTERİMİ ---
        st.write("### 🏆 Kazanılan Başarılar")
        st.markdown('<div class="badge-container">', unsafe_allow_html=True)
        for isim, icon, desc, tier in st.session_state.gs['rozetler']:
            st.markdown(f"""
                <div class="badge-card-premium {tier}">
                    <span class="badge-icon-lg">{icon}</span>
                    <div class="badge-name">{isim}</div>
                    <div class="badge-desc">{desc}</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🔄 Yeni Simülasyon Başlat", use_container_width=True):
            del st.session_state.gs
            st.rerun()
    else:
        # Senaryo ve Karar Mekanizması...
        if st.session_state.gs['aktif_olay'] is None:
            havuz = get_olaylar()
            idx = random.choice([i for i in range(len(havuz)) if i not in st.session_state.kullanilan_indisler])
            st.session_state.kullanilan_indisler.append(idx)
            st.session_state.gs['aktif_olay'] = havuz[idx]

        aktif = st.session_state.gs['aktif_olay']
        st.markdown(f"<div class='game-card'><div class='card-title'>{aktif['baş']}</div><div class='card-text'>{aktif['det']}</div></div>", unsafe_allow_html=True)
        
        col_btn = st.columns(len(aktif['sec']))
        for i, (isim, n, b, it, h) in enumerate(aktif['sec']):
            if col_btn[i].button(isim, use_container_width=True, key=f"btn_{st.session_state.gs['tur']}_{i}"):
                st.session_state.gs['nakit'] += n
                st.session_state.gs['borc'] += b
                st.session_state.gs['itibar'] += it
                # En düşük nakit takibi (Rozet için)
                if st.session_state.gs['nakit'] < st.session_state.gs['en_dusuk_nakit']:
                    st.session_state.gs['en_dusuk_nakit'] = st.session_state.gs['nakit']
                
                # Hisse Güncelleme
                st.session_state.gs['hisse'] = max(5.0, round(st.session_state.gs['hisse'] + h + (it*0.1), 2))
                st.session_state.gs['tur'] += 1
                st.session_state.gs['aktif_olay'] = None
                st.rerun()

with t4:
    st.write("### 📜 Tüm Rozetler ve Gereksinimler")
    st.write("Oyunda açabileceğin tüm başarılar ve seviyeleri:")
    st.markdown("""
    - **Platin Seviye:** Hisse > 150₺ veya İtibar > 180. (Zirve CEO)
    - **Altın Seviye:** Hisse > 100₺ veya Nakit > 15.000₺. (Usta Yönetici)
    - **Gümüş Seviye:** Hisse > 75₺. (Başarılı Yönetici)
    - **Gizli Rozetler:** Krizden muazzam bir dönüş yapmak veya kasayı kuruşu kuruşuna boşaltmak.
    """)
