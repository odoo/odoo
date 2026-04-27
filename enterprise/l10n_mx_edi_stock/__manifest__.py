# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Mexico - Electronic Delivery Guide""",
    'version': '1.2',
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
        'l10n_mx_edi_extended',
        'web_map',
    ],
    "demo": [
        'demo/demo_cfdi.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cfdi_cartaporte.xml',
        'data/l10n_mx_edi_customs_document_type.xml',
        'data/l10n_mx_edi_customs_regime.xml',
        'data/l10n_mx_edi_part.xml',
        'data/l10n_mx_edi.hazardous.material.csv',
        'data/product.unspsc.code.csv',
        'views/l10n_mx_edi_vehicle_views.xml',  # parents l10n_mx_edi_customs_*.xml
        'views/l10n_mx_edi_customs_document_type_views.xml',
        'views/l10n_mx_edi_customs_regime_views.xml',
        'views/l10n_mx_edi_hazardous_material_view.xml',
        'views/product_views.xml',
        'views/report_deliveryslip.xml',  # parents report_cartaporte.xml
        'views/report_cartaporte.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'views/vehicle_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
