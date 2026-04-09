import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st

# --- 1. OLDAL KONFIGURÁCIÓ ÉS LETÖLTÉS ---
st.set_page_config(page_title="COVID-19 Átlagolt Szimuláció", layout="wide")
st.title("Magyarországi COVID adatok vs. Első szimulációs csoport átlaga")

URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"
COLUMN_NAMES = ['S', 'E', 'I', 'R', 'D']

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

# --- 2. MAGYAR ADATOK INTERPOLÁCIÓJA ---
df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

df_hun[date_col] = pd.to_datetime(df_hun[date_col])
# Duplikációk kezelése az interpoláció előtt
df_hun = df_hun.groupby(date_col).mean().sort_index()

# Lyukak kitöltése
full_range = pd.date_range(start=df_hun.index.min(), end=df_hun.index.max(), freq='D')
df_hun_daily = df_hun.reindex(full_range)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 3. ELSŐ 10 SZIMULÁCIÓ (series_1) ÁTLAGOLÁSA ---
csv_files = glob.glob(f"{EXTRACT_DIR}/series_1_*.csv")
all_runs_i = []

for file in csv_files:
    # Beolvasás és típuskonverzió a hibák elkerülésére
    df_sim = pd.read_csv(file, header=None, names=COLUMN_NAMES)
    all_runs_i.append(pd.to_numeric(df_sim['I'], errors='coerce'))

# DataFrame-be gyűjtjük és kiszámoljuk az átlagot (várható értéket)
df_series_1_all = pd.concat(all_runs_i, axis=1)
mean_series_1 = df_series_1_all.mean(axis=1, numeric_only=True)

# Dátumozás a magyar adatok kezdőnapjától
sim_dates = pd.date_range(start=df_hun_daily.index.min(), periods=len(mean_series_1), freq='D')
mean_series_1.index = sim_dates

# --- 4. VIZUALIZÁCIÓ ---
fig, ax = plt.subplots(figsize=(12, 6))

# Valós adatok (Fekete vonal és pontok)
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
        label='Magyar valós (interpolált)', color='black', linewidth=2.5, zorder=5)
ax.scatter(df_hun.index, df_hun[val_col], color='gray', s=10, alpha=0.5, label='Mért pontok')

# Első csoport átlaga (Kék vonal)
ax.plot(mean_series_1.index, mean_series_1, 
        label='1. szimulációs csoport (10 futtatás átlaga)', color='#1f77b4', linewidth=2)

ax.set_title("Fertőzöttek száma: Valóság vs. Szimulációs átlag (series_1)", fontsize=14)
ax.set_ylabel("Fertőzöttek száma (I)")
ax.set_xlabel("Dátum")
ax.legend()
ax.grid(True, linestyle='--', alpha=0.6)

st.pyplot(fig)

# --- 5. STATISZTIKA ---
st.info(f"A grafikon {len(csv_files)} darab 'series_1' típusú fájl átlagolásával készült.")
