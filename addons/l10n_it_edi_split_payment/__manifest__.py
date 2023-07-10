{
    'name': 'Italy - E-invoicing (Split Payment)',
    'countries': ['it'],
    'version': '0.1',
    'depends': [
        'l10n_it_edi'
    ],
    'author': 'Odoo',
    'description': """Split Payment handling for the E-invoice implementation for Italy.

Italian companies are required to let the Public Administration partners pay VAT for their invoices,
in an effort to reduce tax-evasion. This law derogates from the EU directives and will apply until 30th June 2026.

Law reference: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=COM%3A2023%3A0342%3AFIN
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/16.0/applications/finance/accounting/fiscal_localizations/localizations/italy.html',
    'data': [],
    'demo': [
        'demo/res_partner_demo.xml',
    ],
    'license': 'LGPL-3',
}
