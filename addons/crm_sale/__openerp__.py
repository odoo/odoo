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
    'name': 'Customer & Supplier Relationship Management',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """Lead and business Opportunity """,

    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['crm'],
    'init_xml': [
         'crm_lead_data.xml',
          'crm_opportunity_data.xml',
    ],
    'update_xml': [
        'wizard/crm_lead_to_partner_view.xml',
        'wizard/crm_lead_to_opportunity_view.xml',
        'wizard/crm_opportunity_to_phonecall_view.xml',
        'crm_lead_view.xml',
        'crm_lead_menu.xml',
        'crm_opportunity_view.xml',
        'crm_opportunity_menu.xml',
    ],
    'demo_xml': [
        'crm_lead_demo.xml',
        'crm_opportunity_demo.xml',
    ],
    'test': ['test/test_crm_lead.yml',
            #'test/test_crm_opportunity.yml',
             ],
    'installable': True,
    'active': False,
    'certificate': '0079056041421',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
