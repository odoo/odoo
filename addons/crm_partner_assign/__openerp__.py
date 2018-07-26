# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Partner Assignation & Geolocation',
    'version': '1.0',
    'category': 'Sales',
    'description': """
This is the module used by OpenERP SA to redirect customers to its partners, based on geolocation.
======================================================================================================

This modules lets you geolocate Leads, Opportunities and Partners based on their address.

Once the coordinates of the Lead/Opportunity is known, they can be automatically assigned
to an appropriate local partner, based on the distance and the weight that was assigned to the partner.
    """,
    'depends': ['base_geolocalize', 'crm', 'account', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'res_partner_view.xml',
        'wizard/crm_forward_to_partner_view.xml',
        'wizard/crm_channel_interested_view.xml',
        'crm_lead_view.xml',
        'crm_partner_assign_data.xml',
        'crm_portal_view.xml',
        'portal_data.xml',
        'report/crm_lead_report_view.xml',
        'report/crm_partner_report_view.xml',
    ],
    'demo': [
        'res_partner_demo.xml',
        'crm_lead_demo.xml'
    ],
    'installable': True,
    'auto_install': False,
}
