import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st
import numpy as np

# --- OLDAL BEÁLLÍTÁSA (Streamlit specifikus) ---
st.set_page_config(page_title="COVID-19 Szimulációs Csoportok", layout="wide")
st.title("Magyarországi COVID adatok vs. Szimulációs Forgatókönyvek")
st.markdown("""
Ez az alkalmazás összeveti a valós magyar járványadatokat két különböző szimulációs forgatókönyvvel.
A szimulációknál a 10-10 futtatás **várható értékét (átlag)** és **szórását** ábrázoljuk.
""")

# --- 1. KONFIGURÁCIÓ ÉS LETÖLTÉS (Változatlan) ---
URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"

# A GitHub-os Readme alapján az oszlopok:
# S: Susceptible, E: Exposed, I: Infected, R: Recovered, D: Dead
COLUMN_NAMES = ['S', 'E', 'I', 'R', 'D']

@st.cache_data # Streamlit gyorsítótár
def prepare_data():
    # Letöltés
    for url, name in [(URL_EXCEL, EXCEL_NAME), (URL_ZIP, ZIP_NAME)]:
        if not os.path.exists(name):
            r = requests.get(url)
            with open(name, 'wb') as f:
                f.write(r.content)

    # ZIP kicsomagolása
    if not os.path.exists(EXTRACT_DIR):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

prepare_data()

# --- 2. MAGYAR ADATOK FELDOLGOZÁSA (Duplikáció szűréssel - Változatlan) ---
df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

# Dátum formátum és duplikációk kezelése
df_hun[date_col] = pd.to_datetime(df_hun[date_col])
df_hun = df_hun.groupby(date_col).mean() # Összevonás
df_hun = df_hun.sort_index()

# Teljes naptári idősor létrehozása és interpoláció
full_range = pd.date_range(start=df_hun.index.min(), end=df_hun.index.max(), freq='D')
df_hun_daily = df_hun.reindex(full_range)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 3. SZIMULÁCIÓS CSOPORTOK STATISZTIKAI FELDOLGOZÁSA ---
st.subheader("Szimulációs csoportok elemzése")

csv_files = glob.glob(f"{EXTRACT_DIR}/*.csv")
start_date = df_hun_daily.index.min()

# Függvény a csoportok statisztikáinak kiszámítására
def process_simulation_group(file_pattern, group_name):
    group_files = [f for f in csv_files if file_pattern in os.path.basename(f)]
    
    if not group_files:
        st.error(f"Nem találhatók fájlok a(z) {group_name} csoporthoz!")
        return None, None, None

    # Beolvassuk az összes fájlt a csoportból, és csak az 'I' oszlopot tartjuk meg
    all_runs_i = []
    for file in group_files:
        df = pd.read_csv(file, header=None, names=COLUMN_NAMES)
        all_runs_i.append(df['I'])

    # Egyetlen DataFrame-be gyúrjuk őket (oszlopok a futtatások, sorok a napok)
    df_group_i = pd.concat(all_runs_i, axis=1)
    
    # Statisztikák kiszámítása soronként (naponként)
    mean_series = df_group_i.mean(axis=1) # Várható érték
    std_series = df_group_i.std(axis=1)   # Szórás
    
    # Dátumindex hozzárendelése
    sim_dates = pd.date_range(start=start_date, periods=len(mean_series), freq='D')
    mean_series.index = sim_dates
    std_series.index = sim_dates
    
    return mean_series, std_series, len(group_files)

# Kiszámoljuk a két csoport statisztikáit
mean_1, std_1, count_1 = process_simulation_group("series_1", "Forgatókönyv 1 (series_1)")
mean_2, std_2, count_2 = process_simulation_group("series_2", "Forgatókönyv 2 (series_2)")

if count_1 and count_2:
    st.write(f"Sikeresen feldolgozva: {count_1} futtatás a 'series_1'-ből és {count_2} futtatás a 'series_2'-ből.")

# --- 4. VIZUALIZÁCIÓ (Várható érték és Szórás) ---
fig, ax = plt.subplots(figsize=(12, 7))

# 1. Magyar interpolált görbe (vastag fekete vonal)
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
        label='Magyar valós adatok (interpolált)', color='black', linewidth=3, zorder=15)

# 2. Eredeti mérési pontok (kisebb pöttyök)
ax.scatter(df_hun.index, df_hun[val_col], 
           label='Eredeti adatpontok', color='black', s=8, alpha=0.4, zorder=16)

# Функция az átlag és szórás sáv ábrázolására
def plot_group_stats(ax, mean, std, color, label):
    if mean is not None:
        # Átlagvonal (várható érték)
        ax.plot(mean.index, mean, label=f'{label} (átlag)', color=color, linewidth=2, zorder=10)
        # Szórás sáv (átlag +/- szórás)
        ax.fill_between(mean.index, 
                        (mean - std).clip(lower=0), # Ne menjen 0 alá
                        (mean + std), 
                        color=color, alpha=0.2, label=f'{label} (szórás)', zorder=5)

# Csoportok ábrázolása különböző színekkel
plot_group_stats(ax, mean_1, std_1, 'blue', 'Forgatókönyv 1')
plot_group_stats(ax, mean_2, std_2, 'green', 'Forgatókönyv 2')

ax.set_title("COVID-19 Fertőzöttek: Valóság vs. Szimulációs Csoportok", fontsize=16)
ax.set_xlabel("Dátum")
ax.set_ylabel("Fertőzöttek száma (I)")
ax.legend(loc='upper left', bbox_to_anchor=(1, 1)) # Legenda kívül
ax.grid(True, alpha=0.3)

# Megjelenítés Streamlitben
st.pyplot(fig)

# --- 5. ADATBETEKINTŐ (Opcionális) ---
if st.checkbox("Nyers statisztikák mutatása"):
    col1, col2 = st.columns(2)
    with col1:
        st.write("Forgatókönyv 1 (series_1) statisztikái:")
        if mean_1 is not None:
            st.dataframe(pd.DataFrame({'Átlag': mean_1, 'Szórás': std_1}).head(10))
    with col2:
        st.write("Forgatókönyv 2 (series_2) statisztikái:")
        if mean_2 is not None:
            st.dataframe(pd.DataFrame({'Átlag': mean_2, 'Szórás': std_2}).head(10))
