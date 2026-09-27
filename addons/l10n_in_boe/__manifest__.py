{
    'name': "Indian - Bill Of Entry",
    'countries': ['in'],
    'category': "Accounting/Localizations",
    'depends': [
        "l10n_in",
        "stock_landed_costs",
    ],
    'description': """
- Adds Bill of Entry (BOE) support for the Indian localization.
- This Allows users to record import BOE details, link stock receipts, create BOE journal entries, and account for custom duties using landed costs.
""",
    'data': [
        'views/account_move_views.xml',
        'wizard/l10n_in_boe_wizard.xml',
        'security/ir.access.csv',
    ],
    'author': "Odoo S.A.",
    'license': "LGPL-3",
}
