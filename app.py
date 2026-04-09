import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st
import numpy as np

# --- 1. OLDAL KONFIGURÁCIÓ ---
st.set_page_config(page_title="COVID-19 Szimulációs Analízis", layout="wide")
st.title("Magyarországi COVID adatok vs. Szimulációs Csoportok")
st.markdown("A grafikon a magyarországi fertőzöttek számát veti össze két szimulációs forgatókönyv **várható értékével** és **szórásával**.")

# --- 2. ADATOK LETÖLTÉSE ÉS ELŐKÉSZÍTÉSE ---
URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"

# Oszlopnevek a GitHub Readme (S, E, I, R, D) alapján
COLUMN_NAMES = ['S', 'E', 'I', 'R', 'D']

@st.cache_data
def download_and_extract():
    # Letöltés
    for url, name in [(URL_EXCEL, EXCEL_NAME), (URL_ZIP, ZIP_NAME)]:
        if not os.path.exists(name):
            r = requests.get(url)
            with open(name, 'wb') as f:
                f.write(r.content)
    # Kicsomagolás
    if not os.path.exists(EXTRACT_DIR):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

download_and_extract()

# --- 3. MAGYAR ADATOK FELDOLGOZÁSA (INTERPOLÁCIÓ) ---
df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

df_hun[date_col] = pd.to_datetime(df_hun[date_col])

# HIBAJAVÍTÁS: Duplikált dátumok átlagolása
df_hun = df_hun.groupby(date_col).mean()
df_hun = df_hun.sort_index()

# Idősor folytonossá tétele
full_range = pd.date_range(start=df_hun.index.min(), end=df_hun.index.max(), freq='D')
df_hun_daily = df_hun.reindex(full_range)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 4. SZIMULÁCIÓS CSOPORTOK STATISZTIKÁI ---
csv_files = glob.glob(f"{EXTRACT_DIR}/*.csv")
start_date = df_hun_daily.index.min()

def process_group(pattern):
    group_files = [f for f in csv_files if pattern in os.path.basename(f)]
    if not group_files:
        return None, None
    
    all_runs = []
    for f in group_files:
        temp_df = pd.read_csv(f, header=None, names=COLUMN_NAMES)
        # HIBAJAVÍTÁS: Kényszerített numerikus típus az 'I' oszlopra
        s_i = pd.to_numeric(temp_df['I'], errors='coerce')
        all_runs.append(s_i)
    
    df_all = pd.concat(all_runs, axis=1)
    # Várható érték és szórás számítása
    mean_s = df_all.mean(axis=1, numeric_only=True)
    std_s = df_all.std(axis=1, numeric_only=True)
    
    # Dátumozás
    dates = pd.date_range(start=start_date, periods=len(mean_s), freq='D')
    mean_s.index = dates
    std_s.index = dates
    return mean_s, std_s

mean_1, std_1 = process_group("series_1")
mean_2, std_2 = process_group("series_2")

# --- 5. VIZUALIZÁCIÓ ---
fig, ax = plt.subplots(figsize=(12, 6))

# Valós adatok
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], label='Magyar valós (interpolált)', color='black', linewidth=3, zorder=10)
ax.scatter(df_hun.index, df_hun[val_col], color='black', s=10, alpha=0.3, zorder=11)

# Forgatókönyv 1 (Kék)
if mean_1 is not None:
    ax.plot(mean_1.index, mean_1, label='Forgatókönyv 1 (Várható érték)', color='#1f77b4', linewidth=2)
    ax.fill_between(mean_1.index, (mean_1 - std_1).clip(lower=0), (mean_1 + std_1), color='#1f77b4', alpha=0.2, label='Forgatókönyv 1 (Szórás)')

# Forgatókönyv 2 (Zöld)
if mean_2 is not None:
    ax.plot(mean_2.index, mean_2, label='Forgatókönyv 2 (Várható érték)', color='#2ca02c', linewidth=2)
    ax.fill_between(mean_2.index, (mean_2 - std_2).clip(lower=0), (mean_2 + std_2), color='#2ca02c', alpha=0.2, label='Forgatókönyv 2 (Szórás)')

ax.set_title("COVID-19 Fertőzöttek: Valóság vs. Szimulációs csoportok", fontsize=14)
ax.set_ylabel("Fertőzöttek száma (I)")
ax.grid(True, linestyle='--', alpha=0.6)
ax.legend()

st.pyplot(fig)

# --- 6. ADATTÁBLÁZATOK ---
with st.expander("Nyers statisztikai adatok megtekintése"):
    col1, col2 = st.columns(2)
    if mean_1 is not None:
        col1.write("Forgatókönyv 1")
        col1.dataframe(pd.DataFrame({"Átlag": mean_1, "Szórás": std_1}).head(10))
    if mean_2 is not None:
        col2.write("Forgatókönyv 2")
        col2.dataframe(pd.DataFrame({"Átlag": mean_2, "Szórás": std_2}).head(10))
