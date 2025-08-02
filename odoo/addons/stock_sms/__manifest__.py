# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock - SMS",
    'summary': 'Send text messages when final stock move',
    'description': "Send text messages when final stock move",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['stock', 'sms'],
    'data': [
        'data/sms_data.xml',
        'views/res_config_settings_views.xml',
        'wizard/confirm_stock_sms_views.xml',
        'security/ir.model.access.csv',
        'security/sms_security.xml',
    ],
    'auto_install': True,
    'post_init_hook': '_assign_default_sms_template_picking_id',
    'license': 'LGPL-3',
}
