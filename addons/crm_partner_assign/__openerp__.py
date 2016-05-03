# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Partner Assignation & Geolocation',
    'category': 'Customer Relationship Management',
    'description': """
This is the module used by Odoo SA to redirect customers to its partners, based on geolocation.
======================================================================================================

This modules lets you geolocate Leads, Opportunities and Partners based on their address.

Once the coordinates of the Lead/Opportunity is known, they can be automatically assigned
to an appropriate local partner, based on the distance and the weight that was assigned to the partner.
    """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base_geolocalize', 'crm', 'account', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/crm_partner_assign_security.xml',
        'views/res_partner_views.xml',
        'wizard/crm_lead_forward_to_partner_views.xml',
        'wizard/crm_lead_channel_interested_views.xml',
        'views/crm_lead_views.xml',
        'data/crm_partner_assign_data.xml',
        'views/crm_portal_views.xml',
        'report/crm_lead_report_views.xml',
        'report/crm_partner_report_views.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/crm_lead_demo.xml'
    ],
    'test': ['test/partner_assign.yml'],
}
