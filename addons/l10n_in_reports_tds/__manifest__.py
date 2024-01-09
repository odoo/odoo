# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'TDS - India',
    'category': 'Accounting',
    'description': """Streamlines TDS entry management.""",
    'summary': """
        Tax deducted at source - India
    """,
    'countries': ['in'],
    'version': '1.0',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': True,
    'depends': ['l10n_in'],
    'data': [
        'wizard/tds_entry_wizard.xml',
        'security/ir.model.access.csv',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_in_reports_tds/static/src/template.xml',
        ],
    },
}
