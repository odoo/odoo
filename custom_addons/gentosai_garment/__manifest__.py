# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Gentosai Garment Workflow',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Garment production stages for manufacturing orders',
    'depends': ['mrp'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'author': 'Gentosai',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
