
import csv
import re
import unicodedata

INPUT_FILE = "/home/pablo/odoo/scripts/accounts.csv"
def odoo_import_id(uuid):
    if not uuid:
        return ''
    return f"__import__.legacy_account_{uuid.replace('-', '_').lower()}"
OUTPUT_FILE = "/home/pablo/odoo/scripts/res_partner_odoo.csv"
LOG_FILE = "/home/pablo/odoo/scripts/conversion_log.txt"
def slugify(value):
    value = value.lower()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-z0-9]+', '_', value).strip('_')
    return value

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
        "id",
        "name",
        "is_company",
        "parent_id",
        "parent_name",
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
        "bank_ids/acc_number",
        "trade_name",
        "billing_invoice_email",
        "billing_sepa_signed",
        "lopd_signed",
        "bono_informatica",
        "mantenimiento_total_informatica",
        "mantenimiento_centralita_fisica",
        "mantenimiento_centralita_cloud",
        "mantenimiento_vpn",
        "acronis",
        "antivirus",
        "office_365",
        "incidencias_cobro"
    ]

    writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()


    # Primer pase: construir mapeo nombre->id y uuid->id
    name_to_id = {}
    uuid_to_id = {}
    all_rows = list(reader)
    for row in all_rows:
        name = clean(row.get("name"))
        vat = clean(row.get("new_cif"))
        uuid = clean(row.get("accountid"))
        if not name:
            continue
        if vat:
            base_id = slugify(f"{name}_{vat}")
        else:
            base_id = slugify(name)
        # Garantizar unicidad
        id_final = base_id
        i = 2
        while id_final in name_to_id.values():
            id_final = f"{base_id}_{i}"
            i += 1
        name_to_id[name] = id_final
        if uuid:
            uuid_to_id[uuid] = id_final

    # Segundo pase: escribir datos con parent_id correcto
    for row in all_rows:
        processed += 1
        name = clean(row.get("name"))
        if not name:
            errors += 1
            logfile.write(f"Registro sin nombre en fila {processed}\n")
            continue
        vat = clean(row.get("new_cif"))
        uuid = clean(row.get("accountid"))
        if vat and vat in seen_vats:
            duplicates += 1
            logfile.write(f"DUPLICADO CIF {vat} - {name}\n")
            continue
        if vat:
            seen_vats.add(vat)
        iban = clean_iban(row.get("contel_iban"))
        cuenta = clean_iban(row.get("new_numerodecuentabancaria"))
        cuenta_final = iban if iban else cuenta
        parent_name = clean(row.get("parentaccountidname"))
        parent_uuid = clean(row.get("parentaccountid"))
        # Buscar id de la cuenta primaria (por UUID o nombre), solo si existe exactamente como id
        parent_id = ""
        candidate_id = ""
        if parent_uuid and parent_uuid in uuid_to_id:
            candidate_id = uuid_to_id[parent_uuid]
        elif parent_name and parent_name in name_to_id:
            candidate_id = name_to_id[parent_name]
        # Validar que el ID existe como id en el propio archivo y es Odoo import ID completo
        all_ids = set(name_to_id.values()) | set(uuid_to_id.values())
        if candidate_id and candidate_id in all_ids:
            if candidate_id.startswith("__import__.legacy_account_") and len(candidate_id) > 30:
                parent_id = candidate_id
        # Si no hay match exacto, dejar parent_id vacío

        # El id principal será el Odoo import id si hay UUID, si no, slug
        if uuid:
            id_final = odoo_import_id(uuid)
        elif vat:
            id_final = slugify(f"{name}_{vat}")
        else:
            id_final = slugify(name)
        # Garantizar unicidad (solo para slugs, Odoo import id por UUID es único)
        if not uuid:
            i = 2
            base_id = id_final
            while id_final in name_to_id.values():
                id_final = f"{base_id}_{i}"
                i += 1
        name_to_id[name] = id_final
        if uuid:
            uuid_to_id[uuid] = id_final

        # Campos booleanos y mapeo
        trade_name = clean(row.get("new_marcacomercial"))
        billing_invoice_email = clean(row.get("contel_emailfacturacion"))
        billing_sepa_signed = row.get("contel_sepafirmado")
        lopd_signed = row.get("contel_lopdfirmada")
        bono_informatica = row.get("contel_mantenimientoinformatica")
        mantenimiento_total_informatica = row.get("contel_mantenimientototalinformatica")
        mantenimiento_centralita_fisica = row.get("contel_mantenimientocentralitafisica")
        mantenimiento_centralita_cloud = row.get("contel_mantenimientototalinformatica_cloud")
        mantenimiento_vpn = row.get("contel_mantenimientovpn")
        acronis = row.get("contel_acronis")
        antivirus = row.get("contel_antivirus")
        office_365 = row.get("contel_office365")
        incidencias_cobro = row.get("contel_incidenciascobro")

        def bool_field(val):
            if val is None:
                return ""
            v = str(val).strip().lower()
            if v in ("true", "1", "si", "sí", "yes", "y", "s"):
                return "True"
            if v in ("false", "0", "no", "n"):
                return "False"
            return ""

        writer.writerow({
            "id": name_to_id[name],
            "name": name,
            "is_company": "1" if not parent_id else "0",
            "parent_id": parent_id,
            "parent_name": parent_name,
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
            "bank_ids/acc_number": cuenta_final,
            "trade_name": trade_name,
            "billing_invoice_email": billing_invoice_email,
            "billing_sepa_signed": bool_field(billing_sepa_signed),
            "lopd_signed": bool_field(lopd_signed),
            "bono_informatica": bool_field(bono_informatica),
            "mantenimiento_total_informatica": bool_field(mantenimiento_total_informatica),
            "mantenimiento_centralita_fisica": bool_field(mantenimiento_centralita_fisica),
            "mantenimiento_centralita_cloud": bool_field(mantenimiento_centralita_cloud),
            "mantenimiento_vpn": bool_field(mantenimiento_vpn),
            "acronis": bool_field(acronis),
            "antivirus": bool_field(antivirus),
            "office_365": bool_field(office_365),
            "incidencias_cobro": bool_field(incidencias_cobro)
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