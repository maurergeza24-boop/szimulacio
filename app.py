import pandas as pd
import matplotlib.pyplot as plt
import requests
import zipfile
import os
import glob

# --- 1. KONFIGURÁCIÓ ÉS LETÖLTÉS ---
URL_EXCEL = "https://users.itk.ppke.hu/~regiszo/korona_hun.xlsx"
URL_ZIP = "https://users.itk.ppke.hu/~regiszo/covid_data.zip"
EXCEL_NAME = "korona_hun.xlsx"
ZIP_NAME = "covid_data.zip"
EXTRACT_DIR = "covid_data"

def download_file(url, filename):
    if not os.path.exists(filename):
        print(f"Letöltés: {filename}...")
        r = requests.get(url)
        with open(filename, 'wb') as f:
            f.write(r.content)
    else:
        print(f"{filename} már létezik, kihagyás.")

download_file(URL_EXCEL, EXCEL_NAME)
download_file(URL_ZIP, ZIP_NAME)

# --- 2. MAGYAR ADATOK FELDOLGOZÁSA ÉS INTERPOLÁCIÓ ---
print("Magyar adatok feldolgozása...")
df_hun = pd.read_excel(EXCEL_NAME)

# Dátum oszlop automatikus azonosítása és indexelése
date_col = df_hun.columns[0]
val_col = df_hun.columns[1]
df_hun[date_col] = pd.to_datetime(df_hun[date_col])
df_hun = df_hun.set_index(date_col).sort_index()

# Folytonos idősor létrehozása (napi szinten)
full_range = pd.date_range(start=df_hun.index.min(), end=df_hun.index.max(), freq='D')
df_hun_daily = df_hun.reindex(full_range)

# Lineáris interpoláció a lyukak kitöltésére
df_hun_daily['interpolated'] = df_hun_daily[val_col].interpolate(method='linear')

# --- 3. SZIMULÁCIÓS ADATOK KICSOMAGOLÁSA ÉS BEOLVASÁSA ---
if not os.path.exists(EXTRACT_DIR):
    print("ZIP kicsomagolása...")
    with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
        zip_ref.extractall(".")

csv_files = glob.glob(f"{EXTRACT_DIR}/*.csv")
simulations = {}

for file in csv_files:
    name = os.path.basename(file).replace('.csv', '')
    simulations[name] = pd.read_csv(file)

print(f"Beolvasva {len(simulations)} szimulációs fájl.")

# --- 4. VIZUALIZÁCIÓ ---
plt.figure(figsize=(14, 7))

# Interpolált magyar görbe
plt.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
         label='Magyar adatok (interpolált)', color='red', linewidth=2, zorder=5)

# Eredeti adatpontok (ahol volt mérés)
plt.scatter(df_hun.index, df_hun[val_col], 
            label='Eredeti mérések', color='darkred', s=15, alpha=0.5, zorder=6)

# Opcionális: Az első szimuláció kirajzolása összehasonlításképp
# (Feltételezve, hogy a szimulációban is van 'day' és 'infected' jellegű oszlop)
# first_sim = list(simulations.keys())[0]
# plt.plot(simulations[first_sim].iloc[:,0], simulations[first_sim].iloc[:,1], 
#          label=f'Szimuláció: {first_sim}', linestyle='--', alpha=0.7)

plt.title('COVID-19 Fertőzöttek: Valós adatok interpolációval', fontsize=14)
plt.xlabel('Dátum', fontsize=12)
plt.ylabel('Fertőzöttek száma', fontsize=12)
plt.legend()
plt.grid(True, which='both', linestyle='--', alpha=0.5)
plt.tight_layout()

# Mentés GitHub-hoz vagy megjelenítés
plt.savefig('covid_analysis_plot.png')
plt.show()

print("Kész! Az ábra elmentve 'covid_analysis_plot.png' néven.")
