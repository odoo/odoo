# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Mexico - Electronic Delivery Guide - Version 3.0""",
    'countries': ['mx'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': "Version 3.0 of the delivery guide (Complemento XML Carta de Porte).",
    'depends': ['l10n_mx_edi_stock'],
    'data': [
        'data/cfdi_cartaporte.xml',
        'views/l10n_mx_edi_vehicle_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
