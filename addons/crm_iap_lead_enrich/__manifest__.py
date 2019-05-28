# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Enrichment',
    'summary': 'Enrich Leads/Opportunities using email address domain',
    'category': 'Sales/CRM',
    'depends': [
        'iap',
        'crm',
    ],
    'data': [
        'data/ir_cron.xml',
        'data/mail_data.xml',
        'views/res_config_settings_views.xml',
    ],
}
