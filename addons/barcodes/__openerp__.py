{
    'name': 'Barcodes',
    'version': '1.0',
    'category': '',
    'sequence': 6,
    'summary': 'Barcode Nomenclatures Setup',
    'description': """

=======================

This module defines barcode nomenclatures whose rules identify e.g. products, locations.
It contains the following features:
- Barcode patterns to identify barcodes containing a numerical value (e.g. weight, price)
- Definitin of barcode aliases that allow to identify the same product with different barcodes
- Unlimited barcode patterns and definitions. 
- Barcode EAN13 encoding supported
""",
    'author': 'OpenERP SA',
    'depends': ['web'],
    'website': '',
    'data': [
        'data/barcodes_data.xml',
        'barcodes_view.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
