# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Directory Vote',
    'summary': 'Votes data in order to improve directory accuracy',
    'version': '0.1',
    'category': 'Sales/CRM',
    'depends': [
        'iap_crm',
    ],
    'data': [
        'data/ir_cron.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
