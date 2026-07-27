# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'author': 'Odoo S.A.',
    'name': 'Greece - myDATA Delivery Note',
    'category': 'Accounting/Localizations',
    'summary': """Transmit Greece myDATA EDI for Delivery Notes""",
    'description': """
        This module allows transmitting electronic Delivery Notes
        to Greece's tax authority myDATA platform.
    """,
    'countries': ['gr'],
    'depends': ['l10n_gr_edi', 'stock', 'sale', 'sale_stock'],
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'views/report_deliveryslip.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
