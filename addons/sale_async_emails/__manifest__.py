# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sales - Async Emails",
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': "Send order status emails asynchronously",
    'depends': ['sale'],
    'data': [
        'data/ir_cron.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
