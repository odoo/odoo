# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Enrichment',
    'summary': 'Enrich Leads/Opportunities using email adrress domain',
    'category': 'CRM',
    'depends': ['crm_iap_lead'],
    'data': [
        'data/mail_data.xml',
        'data/mail_template.xml',
        'data/crm_iap_enrich_cron.xml',
        'views/crm_iap_lead_enrichment_email.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': [
    ],
}
