# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Mexico - Electronic Delivery Guide Comex - Version 3.0""",
    'countries': ['mx'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
    Bridge module to extend Version 3.0 of the delivery guide (Complemento XML Carta de Porte).
    - Exported goods (COMEX).
    - Extended address fields.
    """,
    'depends': [
        'l10n_mx_edi_stock_30',
        'l10n_mx_edi_stock_extended',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cfdi_cartaporte.xml',
        'data/l10n_mx_edi_customs_document_type.xml',
        'data/l10n_mx_edi_customs_regime.xml',
        'views/l10n_mx_edi_customs_document_type_views.xml',
        'views/l10n_mx_edi_customs_regime_views.xml',
        'views/product_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
