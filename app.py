import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
import plotly.graph_objects as go

st.set_page_config(page_title="Epidemiológiai Vizualizáció", layout="wide")

st.title("Valós és Szimulált Adatok Vizualizációja (.csv verzió)")

# 1. Google Sheets beolvasása
SHEET_URL = "https://docs.google.com/spreadsheets/d/1e4VEZL1xvsALoOIq9V2SQuICeQrT5MtWfBm32ad7i8Q/export?format=csv&gid=311133316"

@st.cache_data
def load_real_data(url):
    return pd.read_csv(url)

try:
    df_real = load_real_data(SHEET_URL)
    categories = df_real.columns.tolist()[1:] 
    st.sidebar.success("Google Sheet adatok betöltve.")
except Exception as e:
    st.error(f"Hiba a Google Sheet betöltésekor: {e}")
    categories = []

# 2. ZIP fájl feltöltése
uploaded_file = st.sidebar.file_uploader("Töltsd fel a szimulációs .zip fájlt", type="zip")

# Mapping a kért kalkulációkhoz
mapping = {
    "Kórházi ápoltak száma": lambda df: df['I5_h'] + df['I6_h'] + df['R_h'],
    "Napi új fertőzöttek száma": lambda df: df['NI'],
    "Aktív fertőzöttek száma": lambda df: df['E'] + df['I1'] + df['I2'] + df['I3'] + df['I4'] + df['I5_h'] + df['I6_h'],
    "Karanténozottak száma": lambda df: df['Q']
}

selected_category = st.selectbox("Válassz egy szempontot a vizualizációhoz:", categories)

if uploaded_file and selected_category:
    sim_data_list = []
    
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            # Csak a .csv fájlokat keressük (kizárva a rejtett rendszermappákat)
            csv_files = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__')][:10]

            if not csv_files:
                st.error("Nem található .csv fájl a feltöltött ZIP-ben!")
            else:
                # Debug: megnézzük az első fájl oszlopait
                with z.open(csv_files[0]) as f:
                    test_df = pd.read_csv(f)
                    st.sidebar.write("CSV oszlopai:", test_df.columns.tolist())

                for file in csv_files:
                    with z.open(file) as f:
                        # Beolvasás (ha vessző helyett pontosvessző az elválasztó, a sep=None kitalálja)
                        df_sim = pd.read_csv(f, sep=None, engine='python')
                        
                        if selected_category in mapping:
                            try:
                                sim_data_list.append(mapping[selected_category](df_sim))
                            except KeyError as ke:
                                st.error(f"Hiányzó oszlop a CSV-ben: {ke}")
                                break
                        elif selected_category in df_sim.columns:
                            sim_data_list.append(df_sim[selected_category])

        if sim_data_list:
            sim_matrix = pd.concat(sim_data_list, axis=1)
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

            # --- PLOTLY GRAFIKON ---
            fig = go.Figure()
            x_axis = df_real.iloc[:, 0]

            # Szimulációk (10 db vékony vonal)
            for i in range(sim_matrix.shape[1]):
                fig.add_trace(go.Scatter(x=x_axis, y=sim_matrix.iloc[:, i], 
                             mode='lines', line=dict(color='rgba(150,150,150,0.2)', width=1),
                             showlegend=False))

            # Valós adatok
            fig.add_trace(go.Scatter(x=x_axis, y=df_real[selected_category], 
                         mode='lines+markers', line=dict(color='blue', width=3),
                         name='Valós értékek'))

            # Átlag
            fig.add_trace(go.Scatter(x=x_axis, y=sim_mean, 
                         mode='lines', line=dict(color='red', width=3),
                         name='Szimulált átlag'))

            # Felső szórás
            fig.add_trace(go.Scatter(x=x_axis, y=upper_dev_line, 
                         mode='lines', line=dict(color='green', width=2, dash='dash'),
                         name='Felső szórás'))

            # Alsó szórás
            fig.add_trace(go.Scatter(x=x_axis, y=lower_dev_line, 
                         mode='lines', line=dict(color='orange', width=2, dash='dash'),
                         name='Alsó szórás'))

            fig.update_layout(
                title=f"{selected_category} elemzése",
                xaxis_title="Idő",
                yaxis_title="Érték",
                hovermode="x unified",
                template="plotly_white",
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Hiba történt: {e}")
else:
    st.info("Töltsd fel a CSV-ket tartalmazó ZIP fájlt!")
