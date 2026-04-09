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

uploaded_file = st.sidebar.file_uploader("Töltsd fel a szimulációs .zip fájlt", type="zip")
selected_category = st.selectbox("Válassz egy szempontot:", categories)

if uploaded_file and selected_category:
    sim_data_list = []
    cat_lower = selected_category.lower() # Kisbetűs keresés a rugalmasságért
    
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            csv_files = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__')][:10]

            if not csv_files:
                st.error("❌ Nem található .csv fájl a ZIP-ben!")
            else:
                for file in csv_files:
                    with z.open(file) as f:
                        df_sim = pd.read_csv(f, sep=None, engine='python')
                        df_sim = df_sim.apply(pd.to_numeric, errors='coerce')
                        
                        # DINAMIKUS MAPPING (Kulcsszavak alapján)
                        res = None
                        try:
                            if "kórház" in cat_lower or "ápolt" in cat_lower:
                                res = df_sim['I5_h'] + df_sim['I6_h'] + df_sim['R_h']
                            elif "új fertőzött" in cat_lower or "ni" in cat_lower:
                                res = df_sim['NI']
                            elif "aktív" in cat_lower:
                                res = df_sim['E'] + df_sim['I1'] + df_sim['I2'] + df_sim['I3'] + df_sim['I4'] + df_sim['I5_h'] + df_sim['I6_h']
                            elif "karantén" in cat_lower or "q" in cat_lower:
                                res = df_sim['Q']
                            elif selected_category in df_sim.columns:
                                res = df_sim[selected_category]
                            
                            if res is not None:
                                sim_data_list.append(res.reset_index(drop=True))
                        except Exception as e:
                            st.sidebar.error(f"Oszlop hiba a(z) {file} fájlban: {e}")

        if sim_data_list:
            sim_matrix = pd.concat(sim_data_list, axis=1)
            sim_mean = sim_matrix.mean(axis=1)
            
            # Szórás számítás
            upper_dev = [sim_mean[i] + (sim_matrix.iloc[i][sim_matrix.iloc[i] > sim_mean[i]] - sim_mean[i]).mean() if not (sim_matrix.iloc[i][sim_matrix.iloc[i] > sim_mean[i]]).empty else sim_mean[i] for i in range(len(sim_mean))]
            lower_dev = [sim_mean[i] - (sim_mean[i] - sim_matrix.iloc[i][sim_matrix.iloc[i] < sim_mean[i]]).mean() if not (sim_matrix.iloc[i][sim_matrix.iloc[i] < sim_mean[i]]).empty else sim_mean[i] for i in range(len(sim_mean))]

            # --- GRAFIKON ---
            fig = go.Figure()
            x_axis = df_real.iloc[:, 0].reset_index(drop=True)

            # 1. Szimulációk
            for i in range(sim_matrix.shape[1]):
                fig.add_trace(go.Scatter(x=x_axis, y=sim_matrix.iloc[:, i], mode='lines', line=dict(color='rgba(150,150,150,0.15)', width=1), showlegend=False))

            # 2. Valós (Kék)
            fig.add_trace(go.Scatter(x=x_axis, y=df_real[selected_category].reset_index(drop=True), mode='lines+markers', line=dict(color='#1f77b4', width=4), name='Valós értékek'))

            # 3. Átlag (Piros)
            fig.add_trace(go.Scatter(x=x_axis, y=sim_mean, mode='lines', line=dict(color='#d62728', width=3), name='Szimulált átlag'))

            # 4. Szórások
            fig.add_trace(go.Scatter(x=x_axis, y=upper_dev, mode='lines', line=dict(color='#2ca02c', width=2, dash='dot'), name='Felső szórás'))
            fig.add_trace(go.Scatter(x=x_axis, y=lower_dev, mode='lines', line=dict(color='#ff7f0e', width=2, dash='dot'), name='Alsó szórás'))

            fig.update_layout(title=f"Analízis: {selected_category}", xaxis_title="Idő", yaxis_title="Fő", hovermode="x unified", height=650)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Nem találtam a szimulációs fájlokban '{selected_category}' jellegű adatot. Ellenőrizd a CSV oszlopneveit!")
    except Exception as e:
        st.error(f"Váratlan hiba: {e}")
else:
    st.info("Töltsd fel a ZIP fájlt és válassz egy kategóriát!")
