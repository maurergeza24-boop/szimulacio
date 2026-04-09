import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st
import numpy as np

# --- 1. OLDAL KONFIGURÁCIÓ ÉS LETÖLTÉS (Változatlan) ---
st.set_page_config(page_title="COVID-19 Összehasonlítás", layout="wide")
st.title("Magyarországi COVID adatok vs. Szimulációs Átlag (Közös időszak)")
st.markdown("A grafikon kizárólag a valós adatok időintervallumát mutatja be, összevetve azt a szimulációs csoport várható értékével.")

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

# --- 2. MAGYAR ADATOK INTERPOLÁCIÓJA ÉS IDŐSÁV ---
df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

df_hun[date_col] = pd.to_datetime(df_hun[date_col])
# Duplikációk kezelése az interpoláció előtt
df_hun = df_hun.groupby(date_col).mean().sort_index()

# Meghatározzuk a valós adatok idősávját
start_date = df_hun.index.min()
end_date = df_hun.index.max()
st.info(f"A valós adatok idősávja: {start_date.date()} - {end_date.date()}")

# Lyukak kitöltése a teljes időszakra
full_range = pd.date_range(start=start_date, end=end_date, freq='D')
df_hun_daily = df_hun.reindex(full_range)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 3. SZIMULÁCIÓS ÁTLAG (series_1) ÉS IDŐZÍTÉS ---
csv_files = glob.glob(f"{EXTRACT_DIR}/series_1_*.csv")
all_runs_i = []

for file in csv_files:
    # Beolvasás és numerikus típus kényszerítése
    df_sim = pd.read_csv(file, header=None, names=COLUMN_NAMES)
    all_runs_i.append(pd.to_numeric(df_sim['I'], errors='coerce'))

# DataFrame-be gyűjtjük és kiszámoljuk az átlagot (várható értéket)
df_series_1_all = pd.concat(all_runs_i, axis=1)
mean_series_1 = df_series_1_all.mean(axis=1, numeric_only=True)

# --- IDŐZÍTÉS ILLESZTÉSE A VALÓS ADATOKHOZ ---
# A szimuláció 0. napját hozzárendeljük a valós adatok kezdőnapjához
sim_dates = pd.date_range(start=start_date, periods=len(mean_series_1), freq='D')
mean_series_1.index = sim_dates

# Kizárólag a valós adatok idősávjára korlátozzuk a szimulációt
mean_series_1_trimmed = mean_series_1[start_date:end_date]

# --- 4. VIZUALIZÁCIÓ ---
fig, ax = plt.subplots(figsize=(12, 6))

# A) Valós grafikon (vastag fekete vonal és pontok)
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
        label='Valós adatok (interpolált)', color='black', linewidth=3, zorder=10)
ax.scatter(df_hun.index, df_hun[val_col], color='gray', s=10, alpha=0.5, label='Eredeti mérések')

# B) Szimulált grafikon (színes vonal, csak a közös időszakban)
if not mean_series_1_trimmed.empty:
    ax.plot(mean_series_1_trimmed.index, mean_series_1_trimmed, 
            label='Szimulált átlag (1. csoport, 10 futtatás)', color='#1f77b4', linewidth=2.5)
else:
    st.error("A szimulációs idővonal nem illeszkedik a valós adatok idősávjára.")

# Tengelybeállítások
ax.set_title("COVID-19 Fertőzöttek: Valóság vs. Szimuláció (Közös Idősáv)", fontsize=14)
ax.set_ylabel("Fertőzöttek száma (I)")
ax.set_xlabel("Dátum")
# Biztosítjuk, hogy a tengely pontosan a valós adatok határait mutassa
ax.set_xlim(start_date, end_date) 
ax.legend()
ax.grid(True, linestyle='--', alpha=0.6)

st.pyplot(fig)

# Opcionális: Statisztika
if not mean_series_1_trimmed.empty:
    st.info(f"A grafikon {len(csv_files)} darab 'series_1' típusú fájl átlagolásával és időbeli illesztésével készült.")
