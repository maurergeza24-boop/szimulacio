import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st

# --- 1. KONFIGURÁCIÓ ---
st.set_page_config(page_title="COVID Szimuláció Analízis", layout="wide")
st.title("Szimulációs eredmények vs. Valós adatok")

URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"

# A megadott szempontok alapján összeállított oszlopsorrend (példa struktúra)
# Megjegyzés: A pontos oszlopindexek a CSV-ben kulcsfontosságúak. 
# Itt a leírásod szerinti sorrendet követjük.
COLUMN_NAMES = [
    'S', 'E', 'I1', 'I2', 'I3', 'I4', 'I5_h', 'I6_h', 'R_h', 'R', 'D1', 'NI', 
    'T', 'P1', 'P2', 'Q', 'QT', 'NQ', 'MUT0', 'MUT1', 'MUT2', 'MUT3', 'MUT4', 'MUT5'
]

@st.cache_data
def load_data():
    for url, name in [(URL_EXCEL, EXCEL_NAME), (URL_ZIP, ZIP_NAME)]:
        if not os.path.exists(name):
            r = requests.get(url)
            with open(name, 'wb') as f: f.write(r.content)
    if not os.path.exists(EXTRACT_DIR):
        with zipfile.ZipFile(ZIP_NAME, 'r') as z: z.extractall(".")

load_data()

# --- 2. ADATFELDOLGOZÁS ---

# Valós adatok beolvasása
df_hun = pd.read_excel(EXCEL_NAME)
date_col, val_col = df_hun.columns[0], df_hun.columns[1]
df_hun[date_col] = pd.to_datetime(df_hun[date_col])
df_hun = df_hun.groupby(date_col).mean().sort_index()

# Szimulációs adatok beolvasása (series_1 csoport)
csv_files = glob.glob(f"{EXTRACT_DIR}/series_1_*.csv")
all_sim_ni = []
all_sim_active = []

for f in csv_files:
    # A 'low_memory=False' segít a sok oszlop kezelésében
    df = pd.read_csv(f, header=None, names=COLUMN_NAMES, sep=',', index_col=False)
    
    # 1. Napi új fertőzöttek (NI)
    all_sim_ni.append(pd.to_numeric(df['NI'], errors='coerce'))
    
    # 2. Aktív fertőzöttek (E + I1 + I2 + I3 + I4 + I5_h + I6_h)
    active = df[['E', 'I1', 'I2', 'I3', 'I4', 'I5_h', 'I6_h']].sum(axis=1)
    all_sim_active.append(active)

# Átlagok kiszámítása
sim_ni_mean = pd.concat(all_sim_ni, axis=1).mean(axis=1)
sim_active_mean = pd.concat(all_sim_active, axis=1).mean(axis=1)

# --- 3. IDŐSÁV ILLESZTÉSE (A szimuláció a mérvadó) ---
# A szimuláció hossza határozza meg a grafikont
sim_days = len(sim_ni_mean)
start_date = df_hun.index.min()
# Létrehozzuk a szimulált napokhoz tartozó dátumokat
sim_dates = pd.date_range(start=start_date, periods=sim_days, freq='D')

sim_ni_mean.index = sim_dates
sim_active_mean.index = sim_dates

# A valós adatokat hozzávágjuk a szimulált időszakhoz
df_hun_clipped = df_hun[df_hun.index <= sim_dates.max()]
# Interpoláció a lyukakra a valós adaton belül
full_range_clipped = pd.date_range(start=start_date, end=df_hun_clipped.index.max(), freq='D')
df_hun_interp = df_hun_clipped.reindex(full_range_clipped).interpolate()

# --- 4. VIZUALIZÁCIÓ ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# Felső grafikon: Napi új fertőzöttek (NI)
ax1.plot(sim_ni_mean.index, sim_ni_mean, label="Szimulált Napi Új (NI átlag)", color='blue', linewidth=2)
# Megjegyzés: A valós adatot akkor tegyük rá, ha az Excelben is napi új adat van (nem kumulatív)
# Ha az Excel kumulatív, akkor a .diff() függvénnyel kapjuk meg a napi újat
valos_napi = df_hun_interp[val_col].diff().fillna(0)
ax1.bar(df_hun_interp.index, valos_napi, label="Valós Napi Új (Mért)", color='gray', alpha=0.3)
ax1.set_title("Napi új fertőzöttek alakulása")
ax1.legend()

# Alsó grafikon: Aktív fertőzöttek
ax2.plot(sim_active_mean.index, sim_active_mean, label="Szimulált Aktív (E+I1..I6)", color='red', linewidth=2)
ax2.set_title("Aktív fertőzöttek száma (Szimuláció)")
ax2.set_xlabel("Dátum")
ax2.legend()

plt.tight_layout()
st.pyplot(fig)

# --- 5. STATISZTIKA ---
total_pop = 9700000 # Becsült magyar lakosság, ha a modell nem adja meg
cum_sim = sim_ni_mean.sum()
inf_rate = (cum_sim / total_pop) * 100
st.metric("Szimulált átfertőzöttség", f"{inf_rate:.2f}%")
