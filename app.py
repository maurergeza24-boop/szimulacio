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

# Oszlopnevek a megadott dokumentáció alapján
COLUMN_NAMES = ['S', 'E', 'I', 'R', 'D']

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

date_col = df_hun.columns[0]
val_col = df_hun.columns[1]
df_hun[date_col] = pd.to_datetime(df_hun[date_col])
df_hun = df_hun.set_index(date_col).sort_index()

full_range = pd.date_range(start=df_hun.index.min(), end=df_hun.index.max(), freq='D')
df_hun_daily = df_hun.reindex(full_range)
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
    # Beolvasás a dokumentáció szerinti oszlopnevekkel
    # Mivel a CSV-kben valószínűleg nincs fejléc, a 'names' paramétert használjuk
    df_sim = pd.read_csv(file, header=None, names=COLUMN_NAMES)
    simulations[name] = df_sim

print(f"Beolvasva {len(simulations)} szimulációs fájl a megfelelő oszlopnevekkel (S, E, I, R, D).")

# --- 4. VIZUALIZÁCIÓ ---
plt.figure(figsize=(14, 8))

# 1. Magyar adatok (Interpolált)
plt.plot(df_hun_daily.index, df_hun_daily['interpolated'], 
         label='Magyar valós adatok (interpolált)', color='black', linewidth=3, zorder=10)

# 2. Szimulációk ábrázolása (példaként az első 5-öt rajzoljuk ki, hogy átlátható maradjon)
# A szimulációkban a napok számát (index) át kell váltani dátumra az összehasonlításhoz
start_date = df_hun_daily.index.min()

for i, (name, df_sim) in enumerate(list(simulations.items())[:5]):
    # Létrehozunk egy dátumindexet a szimulációnak is
    sim_dates = pd.date_range(start=start_date, periods=len(df_sim), freq='D')
    
    # Az 'I' (Infected/Fertőzött) oszlopot rajzoljuk ki
    plt.plot(sim_dates, df_sim['I'], label=f'Szimuláció: {name} (I)', alpha=0.6)

plt.title('Valós magyar COVID adatok vs. Szimulációs eredmények (I oszlop)', fontsize=14)
plt.xlabel('Dátum', fontsize=12)
plt.ylabel('Fertőzöttek száma', fontsize=12)
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()

plt.savefig('covid_simulation_comparison.png')
plt.show()

print("Kész! A szimulációkat az 'I' oszlop alapján ábrázoltuk.")
