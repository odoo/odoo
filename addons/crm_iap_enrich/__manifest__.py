# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Enrichment',
    'summary': 'Enrich Leads/Opportunities using email address domain',
    'category': 'Sales/CRM',
    'version': '1.1',
    'depends': [
        'iap_crm',
        'iap_mail',
    ],
    'data': [
        'data/ir_cron.xml',
        'data/ir_action.xml',
        'data/mail_templates.xml',
        'views/crm_lead_views.xml',
        'views/res_config_settings_view.xml',
    ],
    'post_init_hook': '_synchronize_cron',
    'auto_install': True,
    'license': 'LGPL-3',
}
