# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'TDS Entry- India',
    'category': 'Accounting',
    'description': """Streamlines TDS entry management.""",
    'summary': """
        Tax deducted at source entry management - India
    """,
    'countries': ['in'],
    'version': '1.0',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': ['l10n_in'],
    'depends': ['l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/tds_entry_wizard.xml',
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_in_tds_entry/static/src/template.xml',
        ],
    },
}
