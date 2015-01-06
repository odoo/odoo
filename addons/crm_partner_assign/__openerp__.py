# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Partner Assignation & Geolocation',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'description': """
This is the module used by OpenERP SA to redirect customers to its partners, based on geolocation.
======================================================================================================

This modules lets you geolocate Leads, Opportunities and Partners based on their address.

Once the coordinates of the Lead/Opportunity is known, they can be automatically assigned
to an appropriate local partner, based on the distance and the weight that was assigned to the partner.
    """,
    'author': 'OpenERP SA',
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
    'test': ['test/partner_assign.yml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
