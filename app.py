import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import plotly.graph_objects as go

st.set_page_config(page_title="Epidemiológiai Vizualizáció", layout="wide")

st.title("Epidemiológiai Adatok Vizualizációja")

# 1. Google Sheets beolvasása
SHEET_URL = "https://docs.google.com/spreadsheets/d/1e4VEZL1xvsALoOIq9V2SQuICeQrT5MtWfBm32ad7i8Q/export?format=csv&gid=311133316"

@st.cache_data
def load_real_data(url):
    df = pd.read_csv(url)
    # Kényszerítjük, hogy a számok számok legyenek (ha esetleg szövegként jönne)
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

try:
    df_real = load_real_data(SHEET_URL)
    categories = df_real.columns.tolist()[1:] 
    st.sidebar.success("✅ Google Sheet betöltve")
except Exception as e:
    st.error(f"Hiba a Google Sheet betöltésekor: {e}")
    categories = []

# 2. ZIP fájl feltöltése
uploaded_file = st.sidebar.file_uploader("Töltsd fel a szimulációs .zip fájlt", type="zip")

# Precíz mapping
mapping = {
    "Kórházi ápoltak száma": lambda df: df['I5_h'] + df['I6_h'] + df['R_h'],
    "Napi új fertőzöttek száma": lambda df: df['NI'],
    "Aktív fertőzöttek száma": lambda df: df['E'] + df['I1'] + df['I2'] + df['I3'] + df['I4'] + df['I5_h'] + df['I6_h'],
    "Karanténozottak száma": lambda df: df['Q']
}

selected_category = st.selectbox("Válassz egy szempontot:", categories)

if uploaded_file and selected_category:
    sim_data_list = []
    
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            csv_files = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__')][:10]

            if not csv_files:
                st.error("❌ Nem található .csv fájl a ZIP-ben!")
            else:
                for file in csv_files:
                    with z.open(file) as f:
                        # sep=None + engine='python' segít a pontosvessző/vessző felismerésben
                        df_sim = pd.read_csv(f, sep=None, engine='python')
                        
                        # Kényszerített numerikus átalakítás (tisztítás)
                        df_sim = df_sim.apply(pd.to_numeric, errors='coerce')
                        
                        if selected_category in mapping:
                            val = mapping[selected_category](df_sim)
                            # Reset index, hogy az X tengely (0, 1, 2...) mindenhol ugyanaz legyen
                            sim_data_list.append(val.reset_index(drop=True))
                        elif selected_category in df_sim.columns:
                            sim_data_list.append(df_sim[selected_category].reset_index(drop=True))

        if len(sim_data_list) > 0:
            # Oszlopokba rendezzük a 10 szimulációt
            sim_matrix = pd.concat(sim_data_list, axis=1)
            
            # Statisztikák (soronkénti átlag)
            sim_mean = sim_matrix.mean(axis=1)
            
            upper_dev_line = []
            lower_dev_line = []
            
            for i in range(len(sim_matrix)):
                row = sim_matrix.iloc[i]
                m = sim_mean.iloc[i]
                
                ups = row[row > m]
                u_val = (ups - m).mean() if not ups.empty else 0
                upper_dev_line.append(m + u_val)
                
                lows = row[row < m]
                l_val = (m - lows).mean() if not lows.empty else 0
                lower_dev_line.append(m - l_val)

            # --- GRAFIKON ---
            fig = go.Figure()
            
            # X tengely: a Google Sheet első oszlopa (pl. Nap vagy Dátum)
            x_axis = df_real.iloc[:, 0].reset_index(drop=True)

            # 1. Halvány szürke szimulációk
            for i in range(sim_matrix.shape[1]):
                fig.add_trace(go.Scatter(x=x_axis, y=sim_matrix.iloc[:, i], 
                             mode='lines', line=dict(color='rgba(150,150,150,0.2)', width=1),
                             name="Szimuláció", showlegend=False))

            # 2. Átlag (Piros)
            fig.add_trace(go.Scatter(x=x_axis, y=sim_mean, 
                         mode='lines', line=dict(color='red', width=3),
                         name='Szimulált átlag'))

            # 3. Valós adatok (Kék) - Biztosítjuk, hogy az index itt is stimmeljen
            real_y = df_real[selected_category].reset_index(drop=True)
            fig.add_trace(go.Scatter(x=x_axis, y=real_y, 
                         mode='lines+markers', line=dict(color='blue', width=3),
                         name='Valós értékek'))

            # 4. Szórások
            fig.add_trace(go.Scatter(x=x_axis, y=upper_dev_line, 
                         mode='lines', line=dict(color='green', width=2, dash='dot'),
                         name='Felső szórás'))
            
            fig.add_trace(go.Scatter(x=x_axis, y=lower_dev_line, 
                         mode='lines', line=dict(color='orange', width=2, dash='dot'),
                         name='Alsó szórás'))

            fig.update_layout(
                title=f"Eredmények: {selected_category}",
                xaxis_title="Időegység",
                yaxis_title="Érték",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Kiválasztottad a szempontot, de nem találok hozzá adatot a CSV-kben.")
            
    except Exception as e:
        st.error(f"⚠️ Hiba a számítás során: {e}")
        st.info("Tipp: Ellenőrizd, hogy a CSV fájlokban nincsenek-e üres sorok vagy fejléc-hibák.")
else:
    st.info("💡 Válasz ki egy szempontot és töltsd fel a ZIP fájlt a folytatáshoz.")
