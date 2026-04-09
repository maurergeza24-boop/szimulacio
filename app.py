import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
import plotly.graph_objects as go

st.set_page_config(page_title="Epidemiológiai Vizualizáció", layout="wide")

st.title("Valós és Szimulált Adatok Vizualizációja")

# 1. Google Sheets beolvasása
SHEET_URL = "https://docs.google.com/spreadsheets/d/1e4VEZL1xvsALoOIq9V2SQuICeQrT5MtWfBm32ad7i8Q/export?format=csv&gid=311133316"

@st.cache_data
def load_real_data(url):
    df = pd.read_csv(url)
    # Feltételezzük, hogy az első oszlop az idő (Dátum vagy Nap)
    return df

try:
    df_real = load_real_data(SHEET_URL)
    categories = df_real.columns.tolist()[1:] # Az első oszlop az X tengely (idő)
    st.success("Google Sheet adatok betöltve.")
except Exception as e:
    st.error(f"Hiba a Google Sheet betöltésekor: {e}")
    categories = []

# 2. ZIP fájl feltöltése
uploaded_file = st.sidebar.file_uploader("Töltsd fel a szimulációs .zip fájlt", type="zip")

# Mapping a kategóriák és a szimulált oszlopok között
# Megjegyzés: Itt a felhasználói szempontokat hozzárendeljük a szimulált logikához
mapping = {
    "Kórházi ápoltak száma": lambda df: df['I5_h'] + df['I6_h'] + df['R_h'],
    "Napi új fertőzöttek száma": lambda df: df['NI'],
    "Aktív fertőzöttek száma": lambda df: df['E'] + df['I1'] + df['I2'] + df['I3'] + df['I4'] + df['I5_h'] + df['I6_h'],
    "Karanténozottak száma": lambda df: df['Q']
}

selected_category = st.selectbox("Válassz egy szempontot a vizualizációhoz:", categories)

if uploaded_file and selected_category:
    sim_data_list = []
    
    with zipfile.ZipFile(uploaded_file, 'r') as z:
        # Csak az első 10 .xlsx fájlt olvassuk be
        excel_files = [f for f in z.namelist() if f.endswith('.xlsx')][:10]
        
        for file in excel_files:
            with z.open(file) as f:
                df_sim = pd.read_excel(f)
                # Kiszámoljuk a kiválasztott szempont szerinti értéket
                if selected_category in mapping:
                    sim_data_list.append(mapping[selected_category](df_sim))
                else:
                    # Ha nincs benne a fix mappingben, keressük meg név alapján
                    if selected_category in df_sim.columns:
                        sim_data_list.append(df_sim[selected_category])

    if sim_data_list:
        # Szimulációk összefűzése számításokhoz
        sim_matrix = pd.concat(sim_data_list, axis=1)
        
        # Statisztikai számítások
        sim_mean = sim_matrix.mean(axis=1)
        
        # Egyedi szórás számítás
        upper_dev = []
        lower_dev = []
        
        for i in range(len(sim_matrix)):
            row = sim_matrix.iloc[i]
            mean_val = sim_mean.iloc[i]
            
            # Felső eltérés: átlag feletti értékek átlagos eltérése
            ups = row[row > mean_val]
            u_val = (ups - mean_val).mean() if not ups.empty else 0
            upper_dev.append(mean_val + u_val)
            
            # Alsó eltérés: átlag alatti értékek átlagos eltérése
            lows = row[row < mean_val]
            l_val = (mean_val - lows).mean() if not lows.empty else 0
            lower_dev.append(mean_val - l_val)

        # 3. Grafikon készítése
        fig = go.Figure()

        # X tengely (idő)
        x_axis = df_real.iloc[:, 0]

        # Szimulált egyedi görbék (halványan)
        for i in range(len(sim_data_list)):
            fig.add_trace(go.Scatter(x=x_axis, y=sim_data_list[i], 
                                     mode='lines', line=dict(color='lightgray', width=1),
                                     name=f'Szimuláció {i+1}', showlegend=False))

        # Valós értékek
        fig.add_trace(go.Scatter(x=x_axis, y=df_real[selected_category], 
                                 mode='lines+markers', line=dict(color='blue', width=3),
                                 name='Valós értékek'))

        # Szimulált átlag
        fig.add_trace(go.Scatter(x=x_axis, y=sim_mean, 
                                 mode='lines', line=dict(color='red', width=2),
                                 name='Szimulált átlag'))

        # Felső szórás
        fig.add_trace(go.Scatter(x=x_axis, y=upper_dev, 
                                 mode='lines', line=dict(color='green', width=1, dash='dash'),
                                 name='Felső szórás'))

        # Alsó szórás
        fig.add_trace(go.Scatter(x=x_axis, y=lower_dev, 
                                 mode='lines', line=dict(color='orange', width=1, dash='dash'),
                                 name='Alsó szórás'))

        fig.update_layout(
            title=f"{selected_category} idősoros alakulása",
            xaxis_title="Idő",
            yaxis_title="Mennyiség",
            legend_title="Jelmagyarázat",
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nem sikerült feldolgozni a szimulációs adatokat. Ellenőrizd a fájlok formátumát!")

else:
    st.info("Kérlek, töltsd fel a .zip fájlt az oldalsávban a vizualizáció elindításához.")
