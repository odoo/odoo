import csv
from convert_accounts_for_odoo import get_country_xmlid, get_state_xmlid

def clean_id(val):
    # Quita espacios y caracteres no permitidos para external_id de Odoo
    return val.replace(' ', '').replace('<', '').replace('>', '').replace(';', '').replace(',', '').replace(':', '').replace('=', '').replace('"', '').replace("'", '').replace('/', '').replace('\\', '').replace('.', '').replace('@', '').replace('?', '').replace('!', '').replace('(', '').replace(')', '').replace('[', '').replace(']', '').replace('{', '').replace('}', '').replace('#', '').replace('$', '').replace('%', '').replace('&', '').replace('*', '').replace('+', '').replace('^', '').replace('`', '').replace('~', '').replace('|', '').replace('--', '-')

def main():
    input_csv = 'accounts.csv'
    output_csv = 'accounts_odoo_res_partner.csv'

    with open(input_csv, newline='', encoding='utf-8') as f_in, \
         open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = [
            'id', 'name', 'is_company', 'company_name', 'country_id/id', 'state_id/id', 'zip', 'city', 'street', 'street2',
            'phone', 'mobile', 'email', 'vat', 'website'
        ]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter=',')
        writer.writeheader()
        def clean_value(val):
            return (val or '').replace('\n', ' ').replace('\r', ' ').replace(';', ',').strip()
        for row in reader:
            account_id = row.get('accountid') or ''
            if not account_id:
                continue
            legacy_id = clean_id(f"legacy_account_{account_id}")
            name = row.get('name', '').strip()
            if not name:
                continue
            country_name = clean_value(row.get('address1_country', ''))
            state_name = clean_value(row.get('address1_stateorprovince', ''))
            out_row = {
                'id': legacy_id,
                'name': clean_value(name),
                'is_company': '1',
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
                'website': clean_value(row.get('websiteurl', '')),
            }
            writer.writerow(out_row)

if __name__ == '__main__':
    main()