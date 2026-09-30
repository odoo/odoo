# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Barcode - GS1 Nomenclature',
    'version': '1.0',
    'category': 'Supply Chain/Inventory',
    'summary': 'Parse barcodes according to the GS1-128 specifications',
    'depends': ['barcodes', 'uom'],
    'data': [
        'data/barcodes_gs1_rules.xml',
        'views/barcodes_view.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'barcodes_gs1_nomenclature/static/src/js/barcode_parser.js',
            'barcodes_gs1_nomenclature/static/src/js/barcode_service.js',
        ],
        'web.assets_unit_tests': [
            'barcodes_gs1_nomenclature/static/src/js/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
