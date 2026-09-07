# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Purchase Analytics',
    'summary': 'Track the costs of purchase orders associated with the analytic account of your projects.',
    'category': 'Services/Project',
    'depends': ['purchase', 'project_account'],
    'demo': [
        'data/project_purchase_demo.xml',
    ],
    'data': [
        'views/project_project.xml',
        'views/purchase_order.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_purchase/static/src/product_catalog/kanban_record.js',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
