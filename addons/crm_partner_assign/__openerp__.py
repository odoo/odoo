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
    'name': 'Partner Geo-Localization',
    'version': '1.0',
    'category': 'Hidden',
    'complexity': "normal",
    'description': """
This is the module used by OpenERP SA to redirect customers to its partners, based on geolocalization.
======================================================================================================

You can geolocalize your opportunities by using this module.

Use geolocalization when assigning opportunities to partners.
Determine the GPS coordinates according to the address of the partner.
The most appropriate partner can be assigned.
You can also use the geolocalization without using the GPS coordinates.
    """,
    'author': 'OpenERP SA',
    'depends': ['crm'],
    'demo_xml': [
        'res_partner_demo.xml',
    ],
    'update_xml': [
        'security/ir.model.access.csv',
        'res_partner_view.xml',
        'wizard/crm_forward_to_partner_view.xml',
        'crm_lead_view.xml',
        'report/crm_lead_report_view.xml',
        'report/crm_partner_report_view.xml',
    ],
    'test': [
        'test/process/partner_assign.yml',
    ],
    'installable': True,
    'active': False,
    'certificate': '00503409558942442061',
    'images': ['images/partner_geo_localization.jpeg','images/partner_grade.jpeg'],
}
