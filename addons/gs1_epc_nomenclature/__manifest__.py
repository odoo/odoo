# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'GS1 - EPC Nomenclature',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Parse EPC tags according to the GS1 TDS specifications',
    'depends': ['barcodes',],
    'data': [
        'security/ir.model.access.csv',
        'data/epc_template_field.xml',
        'data/epc_template_scheme.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'gs1_epc_nomenclature/static/src/*.js',
        ],
    },
    'license': 'LGPL-3',
}
