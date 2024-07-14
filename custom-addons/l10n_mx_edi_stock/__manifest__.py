# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Mexico - Electronic Delivery Guide""",
    'countries': ['mx'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
The delivery guide (Complemento XML Carta de Porte) is needed as a proof
that you are sending goods between A and B.

It is only when a delivery order is validated that you can create the delivery
guide.
    """,
    'depends': [
        'stock_delivery',
        'l10n_mx_edi',
        'web_map',
    ],
    "demo": [
        'demo/res_partner.xml',
        'demo/vehicle.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cfdi_cartaporte.xml',
        'data/l10n_mx_edi_part.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'views/l10n_mx_edi_vehicle_views.xml',
        'views/report_deliveryslip.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
