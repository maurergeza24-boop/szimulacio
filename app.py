import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st
import numpy as np

# --- 1. OLDAL KONFIGURÁCIÓ ÉS ADATOK ---
st.set_page_config(page_title="COVID-19 Forgatókönyvek", layout="wide")
st.title("Magyarországi COVID adatok vs. Szimulációs Átlagok")
st.markdown("A grafikon a valós adatok időszakában mutatja be a két különböző szimulációs csoport várható értékét.")

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

# --- 2. MAGYAR ADATOK ELŐKÉSZÍTÉSE ---
df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

df_hun[date_col] = pd.to_datetime(df_hun[date_col])
df_hun = df_hun.groupby(date_col).mean().sort_index()

start_date = df_hun.index.min()
end_date = df_hun.index.max()

# Interpolált valós adatsor
full_range = pd.date_range(start=start_date, end=end_date, freq='D')
df_hun_daily = df_hun.reindex(full_range)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 3. SZIMULÁCIÓS ÁTLAGOK KISZÁMÍTÁSA ---
csv_files = glob.glob(f"{EXTRACT_DIR}/*.csv")

def get_group_mean(pattern, start_dt, end_dt):
    group_files = [f for f in csv_files if pattern in os.path.basename(f)]
    if not group_files:
        return None
    
    all_runs = []
    for file in group_files:
        df = pd.read_csv(file, header=None, names=COLUMN_NAMES)
        all_runs.append(pd.to_numeric(df['I'], errors='coerce'))
    
    # Átlagolás
    mean_series = pd.concat(all_runs, axis=1).mean(axis=1, numeric_only=True)
    
    # Időbeli illesztés és vágás
    dates = pd.date_range(start=start_dt, periods=len(mean_series), freq='D')
    mean_series.index = dates
    return mean_series[start_dt:end_dt]

mean_1 = get_group_mean("series_1", start_date, end_date)
mean_2 = get_group_mean("series_2", start_date, end_date)

# --- 4. VIZUALIZÁCIÓ ---
fig, ax = plt.subplots(figsize=(12, 6))

# Valós adatok
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
        label='Valós adatok (interpolált)', color='black', linewidth=3, zorder=10)
ax.scatter(df_hun.index, df_hun[val_col], color='black', s=10, alpha=0.3)

# 1. csoport átlaga (Kék)
if mean_1 is not None:
    ax.plot(mean_1.index, mean_1, label='1. szimulációs csoport átlaga', color='#1f77b4', linewidth=2, linestyle='--')

# 2. csoport átlaga (Zöld)
if mean_2 is not None:
    ax.plot(mean_2.index, mean_2, label='2. szimulációs csoport átlaga', color='#2ca02c', linewidth=2, linestyle='--')

ax.set_title("COVID-19 Fertőzöttek: Valóság vs. Két szimulációs forgatókönyv", fontsize=14)
ax.set_ylabel("Fertőzöttek száma (I)")
ax.set_xlabel("Dátum")
ax.set_xlim(start_date, end_date)
ax.legend()
ax.grid(True, linestyle='--', alpha=0.5)

st.pyplot(fig)

# Információ a kijelzőn
st.info(f"Időszak: {start_date.date()} - {end_date.date()}")
