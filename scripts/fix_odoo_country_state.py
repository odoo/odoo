import csv

COUNTRY_MAP = {
    "españa": "base.es",
    "espana": "base.es",
    "spain": "base.es",
    "es": "base.es",
    "": "",
}

STATE_MAP = {
    "asturias": "base.state_es_o",
    "principado de asturias": "base.state_es_o",
    "gasteiz": "base.state_es_vi",  # Álava
    "álava": "base.state_es_vi",
    "alava": "base.state_es_vi",
    "vitoria": "base.state_es_vi",
    "galicia": "",  # Galicia no es provincia, dejar vacío o mapear a la provincia real si puedes
    "a coruña": "base.state_es_c",
    "coruña": "base.state_es_c",
    "lugo": "base.state_es_lu",
    "ourense": "base.state_es_or",
    "pontevedra": "base.state_es_po",
    "madrid": "base.state_es_m",
    "sevilla": "base.state_es_se",
    "gijón": "base.state_es_o",
    "gijon": "base.state_es_o",
    # Añade más provincias según tus datos
    "": "",
}

import csv
from convert_accounts_for_odoo import get_country_xmlid, get_state_xmlid

def fix_csv(input_csv, output_csv):
    with open(input_csv, newline='', encoding='utf-8') as fin, \
         open(output_csv, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        fieldnames = list(reader.fieldnames)
        if 'country_id/id' not in fieldnames:
            fieldnames.append('country_id/id')
        if 'state_id/id' not in fieldnames:
            fieldnames.append('state_id/id')
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            country = row.get('country_id/id', '') or row.get('address1_country', '') or row.get('address2_country', '')
            state = row.get('state_id/id', '') or row.get('address1_stateorprovince', '') or row.get('address2_stateorprovince', '')
            row['country_id/id'] = get_country_xmlid(country)
            row['state_id/id'] = get_state_xmlid(state)
            writer.writerow(row)

if __name__ == '__main__':
    fix_csv('accounts.csv', 'accounts_odoo_res_partner_FIXED.csv')
    fix_csv('contacts.csv', 'contacts_odoo_res_partner_FIXED.csv')