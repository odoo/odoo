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
    'category': 'Sales',
    'description': """
This modules allows you to track your customers/suppliers claims and flames.
It is fully integrated with the email gateway so that you can create
automatically new claims based on incoming emails.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['crm'],
    'init_xml': [
         'crm_claim_data.xml',
    ],

    'update_xml': [
        'crm_claim_view.xml',
        'crm_claim_menu.xml',
        'security/ir.model.access.csv',
        'report/crm_claim_report_view.xml',
    ],
    'demo_xml': [
        'crm_claim_demo.xml',
    ], 
    'test': ['test/test_crm_claim.yml'], 
    'installable': True,
    'active': False,
    'certificate' : '00612027414703404749',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
