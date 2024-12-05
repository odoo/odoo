# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gelato",
    'summary': "Gelato POD Integration  ",
    'description': """This module allows to easily use Gelato.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale_management', 'delivery'],
    'auto_install': True,
    'license': 'LGPL-3',
    'data': [
        'data/data.xml',

        'views/delivery_carrier.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ]
}
