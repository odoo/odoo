# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Quality checks with IoT',
    'category': 'Manufacturing/Internet of Things (IoT)',
    'summary': 'Control the quality of your products with IoT devices',
    'description': """
Use devices connected to an IoT Box to control the quality of your products.
""",
    'depends': ['quality_control', 'quality_iot'],
    'data': [
        'wizard/quality_check_wizard_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
