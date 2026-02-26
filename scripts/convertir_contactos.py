"""
Lista de empresas válidas proporcionada por el usuario. Solo estos nombres serán aceptados como empresa.
"""

# Crear un mapeo empresa + CIF (o UUID) para permitir duplicados y vincular correctamente

PAISES_VALIDOS = {
    "españa": "España",
    "espana": "España",
    "spain": "España",
    "": "España",
}

PROVINCIAS_VALIDAS = {
    "principado de asturias": "Asturias",
    "asturoas": "Asturias",
    "asturias": "Asturias",
    "tenerife": "Santa Cruz de Tenerife",
    "santa cruz de tenerife": "Santa Cruz de Tenerife",
    "barcelona": "Barcelona",
    "madrid": "Madrid",
    "leon": "León",
    "león": "León",
    "zaragoza": "Zaragoza",
    "valencia": "Valencia",
    "murcia": "Murcia",
    "la rioja": "La Rioja",
    "pontevedra": "Pontevedra",
    "vigo": "Pontevedra",
    "gijon": "Asturias",
    "gijón": "Asturias",
    "": "",
}

def normaliza_pais(valor):
    if not valor:
        return "España"
    v = valor.strip().lower()
    return PAISES_VALIDOS.get(v, valor.strip().capitalize())

def normaliza_provincia(valor):
    if not valor:
        return ""
    v = valor.strip().lower()
    return PROVINCIAS_VALIDAS.get(v, valor.strip().capitalize())



import csv
import unicodedata
import re
import os

INPUT_FILE = "/home/pablo/odoo/scripts/contacts.csv"
OUTPUT_FILE = "/home/pablo/odoo/scripts/odoo_contacts.csv"
ACCOUNTS_FILE = "/home/pablo/odoo/scripts/accounts.csv"

def normaliza_nombre_empresa(value):
    if not value:
        return ""
    value = value.strip()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'\s+', ' ', value)
    return value

def slugify(value):
    value = value.lower()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-z0-9]+', '_', value).strip('_')
    return value

def odoo_import_id(uuid):
    if not uuid:
        return ''
    return f"__import__.legacy_account_{uuid.replace('-', '_').lower()}"



# 1. Leer accounts.csv y crear mapeos: UUID -> Odoo ID, nombre -> Odoo ID, Odoo ID -> nombre
uuid_to_odooid = {}
name_to_odooid = {}
odooid_to_name = {}
if os.path.exists(ACCOUNTS_FILE):
    with open(ACCOUNTS_FILE, newline='', encoding='utf-8') as accfile:
        acc_reader = csv.DictReader(accfile, delimiter=';')
        for acc in acc_reader:
            uuid = acc.get("accountid")
            name = acc.get("name")
            odoo_id = acc.get("id")
            if uuid and odoo_id:
                uuid_to_odooid[uuid.strip()] = odoo_id.strip()
            if name and odoo_id:
                name_to_odooid[name.strip()] = odoo_id.strip()
            if odoo_id and name:
                oodid = odoo_id.strip()
                odooid_to_name[oodid] = name.strip()

with open(INPUT_FILE, newline='', encoding='utf-8') as infile, \
    open(OUTPUT_FILE, "w", newline='', encoding='utf-8') as outfile:

    reader = csv.DictReader(infile)
    print("Columnas detectadas en el CSV:", reader.fieldnames)

    # Formato compatible con res.partner Odoo
    fieldnames = [
        "id", "active", "parent_id", "email", "name", "phone", "street", "zip",
        "company_name", "first_name", "mobile", "jobtitle", "city", "country_id/id", "state_id/id"
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=',')
    writer.writeheader()

    empresas_creadas = set()
    used_ids = set()

    for row in reader:
        nombre = row.get("firstname", "")
        apellidos = row.get("lastname", "")
        empresa = (
            row.get("company")
            or row.get("company_name")
            or row.get("parentcustomeridname")
            or row.get("parentaccountidname")
            or row.get("adx_organizationname")
        )
        empresa = normaliza_nombre_empresa(empresa)
        cuenta_uuid = row.get("contel_cuenta") or row.get("parentaccountid")
        parent_id = ""
        # company_name siempre es el nombre limpio
        company_name = empresa
        # parent_id solo si hay match
        if cuenta_uuid and cuenta_uuid.strip() in uuid_to_odooid:
            candidate_id = uuid_to_odooid[cuenta_uuid.strip()]
            if candidate_id.startswith("__import__.legacy_account_") and len(candidate_id) > 30:
                parent_id = candidate_id
        elif empresa and empresa in name_to_odooid:
            candidate_id = name_to_odooid[empresa]
            if candidate_id.startswith("__import__.legacy_account_") and len(candidate_id) > 30:
                parent_id = candidate_id
        # company_name siempre se rellena, aunque no haya match
        email = row.get("emailaddress1", "") or row.get("email", "")
        telefono = row.get("telephone1", "") or row.get("phone", "")
        movil = row.get("mobilephone", "") or row.get("mobile", "")
        puesto = row.get("jobtitle", "") or row.get("function", "")
        calle = row.get("address1_line1", "") or row.get("street", "")
        ciudad = row.get("address1_city", "") or row.get("city", "")
        cp = row.get("address1_postalcode", "") or row.get("zip", "")
        estado = normaliza_provincia(row.get("address1_stateorprovince", "") or row.get("state_id/id", ""))
        pais = normaliza_pais(row.get("address1_country", "") or row.get("country_id/id", ""))

        contacto_id = slugify(f"{nombre}_{apellidos}")
        base_contacto_id = contacto_id
        i = 2
        while contacto_id in used_ids:
            contacto_id = f"{base_contacto_id}_{i}"
            i += 1
        used_ids.add(contacto_id)
        if isinstance(company_name, str) and ',' in company_name:
            company_name = company_name.split(',')[0].strip()
        writer.writerow({
            "id": contacto_id,
            "active": "True",
            "parent_id": parent_id,
            "email": email,
            "name": f"{nombre} {apellidos}".strip(),
            "phone": telefono,
            "street": calle,
            "zip": cp,
            "company_name": company_name,
            "first_name": nombre,
            "mobile": movil,
            "jobtitle": puesto,
            "city": ciudad,
            "country_id/id": pais,
            "state_id/id": estado
        })

print("CSV generado correctamente:", OUTPUT_FILE)