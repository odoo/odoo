# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hungary - E-invoicing Receive Vendor Bills',
    'category': 'Accounting/Localizations',
    'description': """
Electronically receive vendor bills from the NAV (Hungarian Tax Agency).
NAV Documentation: https://onlineszamla.nav.gov.hu/files/container/download/2025.10.09.%20EN_Online%20Invoice%20System%203.0%20Interface%20Specification%20.pdf
    """,
    'depends': ['l10n_hu_edi'],
    'data': [
        'data/template_requests.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'wizard/l10n_hu_edi_receive_bills_wizard_views.xml',
    ],
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'l10n_hu_edi_receive/static/src/views/**/*',
        ],
    }
}
