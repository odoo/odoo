import unicodedata

def clean_external_id(val, prefix=None):
    import re
    if not val:
        return ''
    # Quitar tildes y pasar a minúsculas
    val = unicodedata.normalize('NFKD', val)
    val = ''.join([c for c in val if not unicodedata.combining(c)])
    val = val.lower()
    # Reemplazar cualquier secuencia de caracteres no permitidos por un solo guion bajo
    val = re.sub(r'[^a-z0-9]+', '_', val)
    # Eliminar guiones bajos repetidos y al principio/final
    val = re.sub(r'_+', '_', val)
    val = val.strip('_')
    if prefix:
        return f"{prefix}{val}"
    return val
import csv

# Campos requeridos para contactos (imagen 1)
CONTACT_FIELDS = [
    'id',                # External ID único para Odoo
    'name',              # Nombre completo
    'firstname',         # Nombre de pila
    'lastname',          # Apellidos
    'job_title',         # Puesto
    'parent_id/id',      # Cuenta (empresa relacionada)
    'email',             # Correo electrónico
    'phone',             # Teléfono del trabajo
    'mobile',            # Teléfono móvil
    'street',            # Calle
    'street_number',     # Número
    'city',              # Ciudad
    'zip',               # Código postal
    'state_id/id',       # Estado o provincia (XML-ID)
    'country_id/id',     # País o región (XML-ID)
]

# Campos requeridos para cuentas (imagen 2, 3, 4)
ACCOUNT_FIELDS = [
    'id',                # External ID único para Odoo
    'name',              # Nombre de cuenta
    'vat',               # NIF
    'phone',             # Teléfono
    'website',           # Sitio web
    'street',            # Calle
    'street_number',     # Número
    'city',              # Ciudad
    'zip',               # Código postal
    'state_id/id',       # Estado o provincia (XML-ID)
    'country_id/id',     # País o región (XML-ID)
]

def extract_and_clean_contacts(input_csv, output_csv):
    with open(input_csv, newline='', encoding='utf-8') as fin, \
         open(output_csv, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=CONTACT_FIELDS)
        writer.writeheader()
        for row in reader:
            # External ID limpio
            contactid = row.get('contactid') or row.get('id') or ''
            if contactid:
                ext_id = clean_external_id(contactid, prefix='legacy_contact_')
            else:
                ext_id = clean_external_id(row.get('fullname') or row.get('name') or '', prefix='legacy_contact_')
            # External ID de la empresa (parent)
            parent_accountid = row.get('parent_id/id') or row.get('company') or row.get('contel_cuenta') or row.get('parentaccountid') or ''
            if parent_accountid:
                parent_ext_id = clean_external_id(parent_accountid, prefix='legacy_account_')
            else:
                parent_ext_id = ''
            out_row = {
                'id': ext_id,
                'name': row.get('fullname') or row.get('name') or '',
                'firstname': row.get('firstname') or '',
                'lastname': row.get('lastname') or '',
                'job_title': row.get('jobtitle') or '',
                'parent_id/id': parent_ext_id,
                'email': row.get('emailaddress1') or row.get('email') or '',
                'phone': row.get('telephone1') or row.get('phone') or '',
                'mobile': row.get('mobilephone') or row.get('mobile') or '',
                'street': row.get('address1_line1') or row.get('street') or '',
                'street_number': row.get('address1_line2') or row.get('street_number') or '',
                'city': row.get('address1_city') or row.get('city') or '',
                'zip': row.get('address1_postalcode') or row.get('zip') or '',
                'state_id/id': row.get('state_id/id') or '',
                'country_id/id': row.get('country_id/id') or '',
            }
            writer.writerow(out_row)

def extract_and_clean_accounts(input_csv, output_csv):
    with open(input_csv, newline='', encoding='utf-8') as fin, \
         open(output_csv, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=ACCOUNT_FIELDS)
        writer.writeheader()
        for row in reader:
            accountid = row.get('accountid') or row.get('id') or ''
            if accountid:
                ext_id = clean_external_id(accountid, prefix='legacy_account_')
            else:
                ext_id = clean_external_id(row.get('name') or '', prefix='legacy_account_')
            out_row = {
                'id': ext_id,
                'name': row.get('name') or '',
                'vat': row.get('vat') or row.get('nif') or row.get('esnif') or '',
                'phone': row.get('telephone1') or row.get('phone') or '',
                'website': row.get('websiteurl') or row.get('website') or '',
                'street': row.get('address1_line1') or row.get('street') or '',
                'street_number': row.get('address1_line2') or row.get('street_number') or '',
                'city': row.get('address1_city') or row.get('city') or '',
                'zip': row.get('address1_postalcode') or row.get('zip') or '',
                'state_id/id': row.get('state_id/id') or '',
                'country_id/id': row.get('country_id/id') or '',
            }
            writer.writerow(out_row)

if __name__ == '__main__':
    extract_and_clean_contacts('contacts_odoo_res_partner_FIXED.csv', 'contacts_odoo_res_partner_FINAL.csv')
    extract_and_clean_accounts('accounts_odoo_res_partner_FIXED.csv', 'accounts_odoo_res_partner_FINAL.csv')
