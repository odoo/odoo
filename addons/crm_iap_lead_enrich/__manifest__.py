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
        'data/ir_action.xml',
        'data/mail_data.xml',
        'views/crm_lead_views.xml',
    ],
    'post_init_hook': '_synchronize_cron',
}
