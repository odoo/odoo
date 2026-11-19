# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Greece - myDATA Delivery Note through e-invoo',
    'countries': ['gr'],
    'category': 'Accounting/Localizations/EDI',
    'summary': "Send Greek myDATA Delivery Notes through e-invoo",
    'description': """
        Issue Greek myDATA Delivery Notes (document type 9.3) through the
        e-invoo provider, using the same direct API as customer invoices.
    """,
    'depends': ['l10n_gr_edi_delivery_note', 'l10n_gr_edi_e_invoo_bridge'],
    'data': [
        'views/stock_picking_views.xml',
        'views/report_deliveryslip.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
