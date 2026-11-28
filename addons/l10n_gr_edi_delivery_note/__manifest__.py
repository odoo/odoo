# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Greece - myDATA Delivery Note',
    'countries': ['gr'],
    'category': 'Accounting/Localizations/EDI',
    'summary': "Greece myDATA EDI for Delivery Notes",
    'description': """
        Generate Greek myDATA Delivery Notes (document type 9.3) from validated
        transfers. The transmission itself is handled by a provider module.
    """,
    'depends': ['l10n_gr_edi', 'sale_stock'],
    'data': [
        'data/template.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'views/report_deliveryslip.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
