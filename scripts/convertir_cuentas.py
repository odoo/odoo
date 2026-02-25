import csv
import re

INPUT_FILE = "accounts.csv"
OUTPUT_FILE = "res_partner_odoo.csv"
LOG_FILE = "conversion_log.txt"

PROVINCIAS_VALIDAS = {
    "ASTURIAS": "Asturias",
    "PRINCIPADO DE ASTURIAS": "Asturias",
    "ASTUROAS": "Asturias",
    "LLANERA - PRUVIA": "Asturias",

    "MADRID": "Madrid",
    "BARCELONA": "Barcelona",
    "VALENCIA": "Valencia",
    "MURCIA": "Murcia",
    "ZARAGOZA": "Zaragoza",
    "LEON": "León",
    "LEÓN": "León",
    "LLEIDA": "Lleida",
    "LA RIOJA": "La Rioja",
    "TENERIFE": "Santa Cruz de Tenerife",
    "SANTA CRUZ DE TENERIFE": "Santa Cruz de Tenerife",
    "VIGO": "Pontevedra",
    "GALICIA": "",  # Mejor dejar vacío si no sabemos provincia exacta
}

def clean(value):
    if not value:
        return ""
    value = str(value)
    value = value.replace("\n", " ").replace("\r", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def clean_phone(value):
    value = clean(value)
    if "e+" in value.lower():
        try:
            value = str(int(float(value)))
        except:
            pass
    return value

def clean_zip(value):
    value = clean(value)
    if value.endswith(".0"):
        value = value[:-2]
    return value

def clean_iban(value):
    value = clean(value)
    value = value.replace(" ", "").upper()

    if re.match(r"^ES\d{22}$", value):
        return value
    else:
        return "" 

def normalize_province(value):
    value_clean = clean(value).upper()
    return PROVINCIAS_VALIDAS.get(value_clean, "")

seen_vats = set()
duplicates = 0
errors = 0
processed = 0

with open(INPUT_FILE, newline="", encoding="utf-8") as infile, \
     open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as outfile, \
     open(LOG_FILE, "w", encoding="utf-8") as logfile:

    reader = csv.DictReader(infile)

    fieldnames = [
        "name",
        "is_company",
        "parent_id",
        "vat",
        "email",
        "phone",
        "mobile",
        "street",
        "street2",
        "city",
        "zip",
        "state_id",
        "country_id",
        "bank_ids/acc_number"
    ]

    writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for row in reader:
        processed += 1

        name = clean(row.get("name"))
        if not name:
            errors += 1
            logfile.write(f"Registro sin nombre en fila {processed}\n")
            continue

        vat = clean(row.get("new_cif"))

        if vat and vat in seen_vats:
            duplicates += 1
            logfile.write(f"DUPLICADO CIF {vat} - {name}\n")
            continue

        if vat:
            seen_vats.add(vat)

        iban = clean_iban(row.get("contel_iban"))
        cuenta = clean_iban(row.get("new_numerodecuentabancaria"))
        cuenta_final = iban if iban else cuenta

        parent = clean(row.get("parentaccountidname"))

        writer.writerow({
            "name": name,
            "is_company": "1" if not parent else "0",
            "parent_id": parent,
            "vat": vat,
            "email": clean(row.get("emailaddress1")),
            "phone": clean_phone(row.get("telephone1")),
            "mobile": clean_phone(row.get("telephone2")),
            "street": clean(row.get("address1_line1")),
            "street2": clean(row.get("address1_line2")),
            "city": clean(row.get("address1_city")),
            "zip": clean_zip(row.get("address1_postalcode")),
            "state_id": normalize_province(row.get("address1_stateorprovince")),
            "country_id": "ES",
            "bank_ids/acc_number": cuenta_final
        })

    logfile.write(f"\nProcesados: {processed}\n")
    logfile.write(f"Duplicados eliminados: {duplicates}\n")
    logfile.write(f"Errores: {errors}\n")

print("✔ Conversión completada")
print(f"Registros procesados: {processed}")
print(f"Duplicados eliminados: {duplicates}")
print(f"Errores: {errors}")
print("Archivo generado:", OUTPUT_FILE)
print("Log generado:", LOG_FILE)