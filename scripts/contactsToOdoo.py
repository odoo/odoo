# contacts_to_odoo.py
import csv
from convert_accounts_for_odoo import get_country_xmlid, get_state_xmlid

# Devuelve dos diccionarios: 
# - id_to_name: accountid -> nombre
# - id_to_legacyid: accountid -> legacy.account_<accountid>
def read_accounts(accounts_csv):
    id_to_name = {}
    id_to_legacyid = {}
    with open(accounts_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_id = row.get('accountid') or ''
            name = row.get('name') or ''
            legacy_account_id = f"legacy.account_{account_id}" if account_id else ''
            if account_id:
                id_to_name[account_id] = name
                id_to_legacyid[account_id] = legacy_account_id
    return id_to_name, id_to_legacyid

def split_name(fullname):
    parts = fullname.strip().split()
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return parts[0], ''
    else:
        return parts[0], ' '.join(parts[1:])


def clean_id(val):
    # Quita espacios y caracteres no permitidos para external_id de Odoo
    return val.replace(' ', '').replace('<', '').replace('>', '').replace(';', '').replace(',', '').replace(':', '').replace('=', '').replace('"', '').replace("'", '').replace('/', '').replace('\\', '').replace('.', '').replace('@', '').replace('?', '').replace('!', '').replace('(', '').replace(')', '').replace('[', '').replace(']', '').replace('{', '').replace('}', '').replace('#', '').replace('$', '').replace('%', '').replace('&', '').replace('*', '').replace('+', '').replace('^', '').replace('`', '').replace('~', '').replace('|', '').replace('--', '-')

def main():
    contacts_csv = 'contacts.csv'
    accounts_csv = 'accounts.csv'
    output_csv = 'contacts_odoo_res_partner.csv'

    account_id_to_name, accountid_to_legacyid = read_accounts(accounts_csv)

    with open(contacts_csv, newline='', encoding='utf-8') as f_in, \
         open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = [
            'id', 'name', 'is_company', 'company_name', 'country_id/id', 'state_id/id', 'zip', 'city', 'street', 'street2',
            'phone', 'mobile', 'email', 'vat', 'parent_id/id', 'website'
        ]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter=',')
        writer.writeheader()
        def clean_value(val):
            return (val or '').replace('\n', ' ').replace('\r', ' ').replace(';', ',').strip()
        for row in reader:
            contact_id = row.get('contactid') or ''
            if not contact_id:
                continue
            legacy_contact_id = clean_id(f"legacy_contact_{contact_id}")
            account_id = row.get('contel_cuenta') or row.get('parentaccountid') or ''
            legacy_account_id = clean_id(f"legacy_account_{account_id}") if account_id else ''
            fullname = row.get('fullname') or row.get('name') or ''
            country_name = clean_value(row.get('address1_country', ''))
            state_name = clean_value(row.get('address1_stateorprovince', ''))
            out_row = {
                'id': legacy_contact_id,
                'name': clean_value(fullname),
                'is_company': '0',
                'company_name': '',
                'country_id/id': get_country_xmlid(country_name),
                'state_id/id': get_state_xmlid(state_name),
                'zip': clean_value(row.get('address1_postalcode', '')),
                'city': clean_value(row.get('address1_city', '')),
                'street': clean_value(row.get('address1_line1', '')),
                'street2': clean_value(row.get('address1_line2', '')),
                'phone': clean_value(row.get('telephone1', '')),
                'mobile': clean_value(row.get('telephone2', '')),
                'email': clean_value(row.get('emailaddress1', '')),
                'vat': clean_value(row.get('new_cif', '')),
                'parent_id/id': legacy_account_id,
                'website': clean_value(row.get('websiteurl', '')),
            }
            writer.writerow(out_row)

if __name__ == '__main__':
    main()