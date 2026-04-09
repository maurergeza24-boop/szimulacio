import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob
import streamlit as st

# --- OLDAL BEÁLLÍTÁSA (Streamlit specifikus) ---
st.set_page_config(page_title="COVID-19 Adat Analízis", layout="wide")
st.title("Magyarországi COVID adatok és Szimulációk")

# --- 1. KONFIGURÁCIÓ ÉS LETÖLTÉS ---
URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"

# A GitHub-os Readme alapján az oszlopok:
# S: Susceptible, E: Exposed, I: Infected, R: Recovered, D: Dead
COLUMN_NAMES = ['S', 'E', 'I', 'R', 'D']

@st.cache_data # Streamlit gyorsítótár, hogy ne töltsön le mindent minden frissítésnél
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

# --- 2. MAGYAR ADATOK FELDOLGOZÁSA (Duplikáció szűréssel) ---
st.subheader("1. Valós magyar adatok interpolálása")

df_hun = pd.read_excel(EXCEL_NAME)
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]

# Dátum formátum és duplikációk kezelése
df_hun[date_col] = pd.to_datetime(df_hun[date_col])

# Azonos dátumok összevonása (átlagolás), hogy elkerüljük a ValueError-t reindexnél
df_hun = df_hun.groupby(date_col).mean()
df_hun = df_hun.sort_index()

# Teljes naptári idősor létrehozása
full_range = pd.date_range(start=df_hun.index.min(), end=df_hun.index.max(), freq='D')
df_hun_daily = df_hun.reindex(full_range)

# Interpoláció (a lyukak kitöltése lineárisan)
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

st.write(f"Adatok feldolgozva: {df_hun_daily.index.min().date()} - {df_hun_daily.index.max().date()}")

# --- 3. SZIMULÁCIÓS ADATOK BEOLVASÁSA ---
csv_files = glob.glob(f"{EXTRACT_DIR}/*.csv")
simulations = {}

for file in csv_files:
    name = os.path.basename(file).replace('.csv', '')
    # Fejléc nélküli CSV beolvasása a megadott oszlopnevekkel
    df_sim = pd.read_csv(file, header=None, names=COLUMN_NAMES)
    simulations[name] = df_sim

# --- 4. VIZUALIZÁCIÓ (Streamlit felületen) ---
fig, ax = plt.subplots(figsize=(12, 6))

# Magyar interpolált görbe
ax.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
        label='Magyar valós adatok (interpolált)', color='red', linewidth=2.5, zorder=10)

# Eredeti mérési pontok
ax.scatter(df_hun.index, df_hun[val_col], 
           label='Eredeti adatpontok', color='darkred', s=10, alpha=0.5, zorder=11)

# Pár szimuláció kirajzolása (I = Infected oszlop)
# A szimulációkat a magyar adatok kezdőnapjához igazítjuk
start_date = df_hun_daily.index.min()
selected_sims = list(simulations.keys())[:3] # Csak az első 3-at, hogy ne legyen káosz

for name in selected_sims:
    df_sim = simulations[name]
    sim_dates = pd.date_range(start=start_date, periods=len(df_sim), freq='D')
    ax.plot(sim_dates, df_sim['I'], label=f'Szimuláció: {name} (I)', alpha=0.6, linestyle='--')

ax.set_title("Fertőzöttek száma: Valóság vs. Szimuláció", fontsize=16)
ax.set_xlabel("Dátum")
ax.set_ylabel("Létszám")
ax.legend()
ax.grid(True, alpha=0.3)

# Megjelenítés Streamlitben
st.pyplot(fig)

# --- 5. ADATBETEKINTŐ ---
if st.checkbox("Nyers adatok mutatása"):
    st.write("Interpolált magyar adatok (első 10 sor):")
    st.dataframe(df_hun_daily.head(10))
