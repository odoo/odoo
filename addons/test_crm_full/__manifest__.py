# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Full Crm Flow',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
This module is intended to test the main crm flows of Odoo, both frontend and
backend. It notably includes IAP bridges modules to test their impact. """,
    'depends': [
        'crm',
        'crm_iap_enrich',
        'crm_iap_mine',
        'crm_sms',
        'event_crm',
        'sale_crm',
        'website_crm',
        'website_crm_iap_reveal',
        'website_crm_partner_assign',
        'website_crm_livechat',
    ],
    'license': 'LGPL-3',
}
