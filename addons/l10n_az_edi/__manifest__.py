{
    'name': "Azerbaijan - E-Invoicing",
    'category': "Accounting/Localizations/EDI",
    'summary': "Electronic invoice (E-Qaimə Faktura, EQF) XML export for Azerbaijan",
    'countries': ['AZ'],
    'description': """
Generates the electronic invoice (E-Qaimə Faktura, EQF) XML of customer invoices, to be uploaded on the e-taxes.gov.az portal.
    """,
    'author': "Odoo S.A.",
    'depends': [
        'l10n_az',
    ],
    'auto_install': ['l10n_az'],
    'data': [
        'security/ir.access.csv',
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'wizard/l10n_az_eqf_error_wizard_views.xml',
    ],
    'license': "LGPL-3",
}
