# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Account Audit Trail',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Account Audit Trail',
    'depends': ['account'],
    'data': [
        'report/audit_trail_report_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}
