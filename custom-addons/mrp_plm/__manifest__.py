# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Lifecycle Management (PLM)',
    'version': '1.0',
    'category': 'Manufacturing/Product Lifecycle Management (PLM)',
    'sequence': 155,
    'summary': """Manage engineering change orders on products, bills of material""",
    'website': 'https://www.odoo.com/app/plm',
    'depends': ['mrp'],
    'description': """
Product Life Management
=======================

* Versioning of Bill of Materials and Products
* Different approval flows possible depending on the type of change order

""",
    'data': [
        'security/mrp_plm.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'data/mrp_data.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_document_views.xml',
        'views/mrp_eco_views.xml',
        'views/product_views.xml',
        'views/mrp_production_views.xml',
        'report/mrp_report_bom_structure.xml',
    ],
    'demo': [
        'data/mrp_demo.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'mrp_plm/static/src/**/*.js',
            'mrp_plm/static/src/**/*.scss',
            'mrp_plm/static/src/**/*.xml',
        ],
    }
}
