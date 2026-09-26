{
    'name': "Georgia - Electronic Invoicing",
    'countries': ['ge'],
    'category': 'Accounting/Localizations/EDI',
    'summary': "E-Invoicing with RS.ge, Georgia's Revenue Service",
    'description': """
RS.ge is the online invoicing system of the Revenue Service of Georgia, where Georgian businesses
register their sales invoices so that they are legally valid.

This module registers your invoices with RS.ge from Odoo, brings the official invoice number back
onto them, tells you when the customer has accepted or rejected one, and lets you correct or cancel
an invoice that has already been registered.
    """,
    'depends': ['l10n_ge', 'account'],
    'data': [
        'security/ir.access.csv',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/l10n_ge_edi_k_invoice_wizard_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
