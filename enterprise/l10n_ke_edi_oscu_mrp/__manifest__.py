# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Kenya ETIMS EDI Manufacturing Integration",
    'countries': ['ke'],
    'summary': """
        Kenya eTIMS Device EDI Manufacturing Integration
    """,
    'description': """
       This module integrates with the Kenyan eTIMS device (OSCU).
    """,
    'author': 'Odoo',
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'license': 'OEEL-1',
    'depends': ['l10n_ke_edi_oscu_stock', 'mrp'],
    'data': [
        'views/mrp_bom_views.xml',
    ],
    'auto_install': True,
}
