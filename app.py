import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
import plotly.graph_objects as go

st.set_page_config(page_title="Epidemiológiai Vizualizáció", layout="wide")

st.title("Valós és Szimulált Adatok Vizualizációja")

# 1. Google Sheets beolvasása
# A gid=311133316 paraméter biztosítja, hogy a helyes fület olvassuk be
SHEET_URL = "https://docs.google.com/spreadsheets/d/1e4VEZL1xvsALoOIq9V2SQuICeQrT5MtWfBm32ad7i8Q/export?format=csv&gid=311133316"

@st.cache_data
def load_real_data(url):
    return pd.read_csv(url)

try:
    df_real = load_real_data(SHEET_URL)
    # Az első oszlop az idő (pl. Nap), a többi a választható kategória
    categories = df_real.columns.tolist()[1:] 
    st.sidebar.success("Google Sheet adatok betöltve.")
except Exception as e:
    st.error(f"Hiba a Google Sheet betöltésekor: {e}")
    categories = []

# 2. ZIP fájl feltöltése
uploaded_file = st.sidebar.file_uploader("Töltsd fel a szimulációs .zip fájlt", type="zip")

# Precíz mapping - győződj meg róla, hogy a Sheet-ben pontosan ezek a nevek szerepelnek!
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
            # Szűrés: csak .xlsx, nem rejtett fájl, nem könyvtár
            all_files = z.namelist()
            excel_files = [f for f in all_files if f.endswith('.xlsx') and not f.startswith('__') and not '/' in f]
            
            # Ha a fájlok mappában vannak a ZIP-en belül, engedélyezzük az elérési utat:
            if not excel_files:
                excel_files = [f for f in all_files if f.endswith('.xlsx') and not f.startswith('__')][:10]
            else:
                excel_files = excel_files[:10]

            if not excel_files:
                st.error("Nem található .xlsx fájl a ZIP-ben!")
            else:
                # Debug infó az oldalsávban (opcionális, segít látni mi van a fájlban)
                with z.open(excel_files[0]) as f:
                    test_df = pd.read_excel(f, engine='openpyxl')
                    st.sidebar.write("Excel oszlopai:", test_df.columns.tolist())

                for file in excel_files:
                    with z.open(file) as f:
                        df_sim = pd.read_excel(f, engine='openpyxl')
                        
                        # Adat kiszámítása a mapping alapján
                        if selected_category in mapping:
                            try:
                                sim_series = mapping[selected_category](df_sim)
                                sim_data_list.append(sim_series)
                            except KeyError as ke:
                                st.error(f"Hiányzó oszlop az Excelben: {ke}")
                                break
                        else:
                            # Ha direkt oszlopnév egyezés van
                            if selected_category in df_sim.columns:
                                sim_data_list.append(df_sim[selected_category])

        if sim_data_list:
            # Adatok összefűzése (idősorok hossza egyezzen!)
            sim_matrix = pd.concat(sim_data_list, axis=1)
            sim_mean = sim_matrix.mean(axis=1)
            
            # Felső és Alsó eltérés számítása
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

            # --- VIZUALIZÁCIÓ ---
            fig = go.Figure()
            x_axis = df_real.iloc[:, 0] # Első oszlop a dátum/idő

            # 1. Szimulált egyedi görbék (Vékony szürke)
            for i, col in enumerate(sim_matrix.columns):
                fig.add_trace(go.Scatter(x=x_axis, y=sim_matrix[col], 
                             mode='lines', line=dict(color='rgba(150,150,150,0.3)', width=1),
                             name=f'Szimuláció {i+1}', showlegend=False))

            # 2. Szimulált átlag (Piros)
            fig.add_trace(go.Scatter(x=x_axis, y=sim_mean, 
                         mode='lines', line=dict(color='red', width=3),
                         name='Szimulált átlag'))

            # 3. Valós értékek (Kék)
            fig.add_trace(go.Scatter(x=x_axis, y=df_real[selected_category], 
                         mode='lines+markers', line=dict(color='blue', width=3),
                         name='Valós értékek'))

            # 4. Felső szórás (Zöld szaggatott)
            fig.add_trace(go.Scatter(x=x_axis, y=upper_dev_line, 
                         mode='lines', line=dict(color='green', width=2, dash='dash'),
                         name='Felső szórás (átlag felettiek átlaga)'))

            # 5. Alsó szórás (Narancs szaggatott)
            fig.add_trace(go.Scatter(x=x_axis, y=lower_dev_line, 
                         mode='lines', line=dict(color='orange', width=2, dash='dash'),
                         name='Alsó szórás (átlag alattiak átlaga)'))

            fig.update_layout(
                title=f"Trendelemzés: {selected_category}",
                xaxis_title=df_real.columns[0],
                yaxis_title="Érték",
                hovermode="x unified",
                template="plotly_white",
                height=700
            )

            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning("A szimulációs adatok beolvasása sikertelen. Ellenőrizd a kiválasztott szempontot és az Excel oszlopneveit!")

    except Exception as e:
        st.error(f"Hiba történt a feldolgozás során: {e}")

else:
    st.info("Töltsd fel a ZIP fájlt és válassz egy szempontot a kezdéshez.")
