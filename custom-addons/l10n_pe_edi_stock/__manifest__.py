# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Peruvian - Electronic Delivery Note""",
    'countries': ['pe'],
    'version': '0.1',
    'summary': 'Electronic Delivery Note for Peru (OSE method) and UBL 2.1',
    'category': 'Accounting/Localizations/EDI',
    'author': 'Vauxoo',
    'license': 'OEEL-1',
    'description': """
The delivery guide (Guía de Remisión) is needed as a proof
that you are sending goods between A and B.

It is only when a delivery order is validated that you can create the delivery
guide.
    """,
    'depends': [
        'stock_delivery',
        'l10n_pe_edi',
    ],
    "demo": [
        'demo/res_partner.xml',
        'demo/vehicle.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/delivery_security.xml',
        'data/edi_delivery_guide.xml',
        'views/product_template_view.xml',
        'views/report_deliveryslip.xml',
        "views/res_config_settings_views.xml",
        "views/res_partner_view.xml",
        'views/stock_picking_views.xml',
        'views/vehicle_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
