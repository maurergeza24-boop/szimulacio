import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st
import numpy as np

# --- 1. OLDAL KONFIGURÁCIÓ ---
st.set_page_config(page_title="COVID-19 Modell Analízis", layout="wide")
st.title("Magyarországi COVID adatok vs. Szimulációs Kumulatív Esetszám")
st.markdown("""
A grafikon a magyarországi összesített fertőzöttszámot veti össze két szimulációs forgatókönyv **kumulatív (C)** görbéjével.
A szimulációk a valós adatok kezdőnapjához lettek igazítva.
""")

# --- 2. ADATOK ELŐKÉSZÍTÉSE ---
URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"

# A README ALAPJÁN A PONTOS OSZLOPSORREND:
# 1:S, 2:L, 3:I, 4:R, 5:D, 6:C (Cumulative), 7:V
COLUMN_NAMES = ['S', 'L', 'I', 'R', 'D', 'C', 'V']

@st.cache_data
def prepare_files():
    for url, name in [(URL_EXCEL, EXCEL_NAME), (URL_ZIP, ZIP_NAME)]:
        if not os.path.exists(name):
            r = requests.get(url)
            with open(name, 'wb') as f:
                f.write(r.content)
    if not os.path.exists(EXTRACT_DIR):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

prepare_files()

# --- 3. MAGYAR ADATOK FELDOLGOZÁSA ---
df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

df_hun[date_col] = pd.to_datetime(df_hun[date_col])
# Duplikált dátumok kezelése (átlagolás)
df_hun = df_hun.groupby(date_col).mean().sort_index()

start_date = df_hun.index.min()
end_date = df_hun.index.max()

# Interpolált valós adatsor a "lyukak" kitöltésére
full_range = pd.date_range(start=start_date, end=end_date, freq='D')
df_hun_daily = df_hun.reindex(full_range)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 4. SZIMULÁCIÓS CSOPORTOK FELDOLGOZÁSA (C oszlop alapján) ---
csv_files = glob.glob(f"{EXTRACT_DIR}/*.csv")

def get_group_mean_cumulative(pattern, start_dt, end_dt):
    group_files = [f for f in csv_files if pattern in os.path.basename(f)]
    if not group_files:
        return None
    
    all_runs_c = []
    for file in group_files:
        # 7 oszlop beolvasása a Readme szerint
        df = pd.read_csv(file, header=None, names=COLUMN_NAMES)
        # A 'C' (6. oszlop) az összesített esetszám, ezt hasonlítjuk a valósághoz
        s_c = pd.to_numeric(df['C'], errors='coerce')
        all_runs_c.append(s_c)
    
    # Csoportszintű átlag kiszámítása
    mean_series = pd.concat(all_runs_c, axis=1).mean(axis=1, numeric_only=True)
    
    # Időbeli illesztés a valós adatok kezdetéhez
    dates = pd.date_range(start=start_dt, periods=len(mean_series), freq='D')
    mean_series.index = dates
    
    # Csak a valós adatok idősávjára vágjuk le
    return mean_series[start_dt:end_dt]

# Statisztikák kiszámítása mindkét csoportra
mean_c1 = get_group_mean_cumulative("series_1", start_date, end_date)
mean_c2 = get_group_mean_cumulative("series_2", start_date, end_date)

# --- 5. VIZUALIZÁCIÓ ---
fig, ax = plt.subplots(figsize=(12, 7))

# VALÓS ADAT: Fekete vonal
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
        label='Valós magyar adatok (Kumulatív)', color='black', linewidth=3, zorder=10)
ax.scatter(df_hun.index, df_hun[val_col], color='black', s=12, alpha=0.3, label='Mért pontok')

# SZIMULÁCIÓ 1 (C oszlop átlaga): Kék
if mean_c1 is not None:
    ax.plot(mean_c1.index, mean_c1, label='Szimuláció 1 (C átlag)', color='#1f77b4', linewidth=2, linestyle='--')

# SZIMULÁCIÓ 2 (C oszlop átlaga): Zöld
if mean_c2 is not None:
    ax.plot(mean_c2.index, mean_c2, label='Szimuláció 2 (C átlag)', color='#2ca02c', linewidth=2, linestyle='--')

# Grafikon finomhangolása
ax.set_title("Összesített fertőzöttek száma: Valóság vs. Modell (C oszlop)", fontsize=16)
ax.set_ylabel("Összes regisztrált fertőzött")
ax.set_xlabel("Dátum")
ax.set_xlim(start_date, end_date) # Pontosan a valós időszakra korlátozzuk a nézetet
ax.grid(True, which='both', linestyle='--', alpha=0.5)
ax.legend(fontsize=11)

# Streamlit megjelenítés
st.pyplot(fig)

# Adat-statisztika megjelenítése
st.info(f"Időszak: {start_date.date()} és {end_date.date()} között.")
with st.expander("Segítség az értelmezéshez"):
    st.write("""
    - **Fekete vonal:** A magyar statisztikákból származó, napi szintre interpolált összesített esetszám.
    - **Szaggatott vonalak:** A szimulációs fájlok 6. oszlopának ('C' - Cumulative Infectious) 10-10 futtatásból számolt átlaga.
    - A szimulációk kezdőpontja (0. nap) a magyar adatok első napjához lett igazítva.
    """)
