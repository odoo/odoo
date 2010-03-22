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
    'name': 'Detailed info on partner form', 
    'version': '1.0', 
    'category': 'Generic Modules/Base', 
    'description': """
This module adds the following one2many fields on the bottom partner form:

    * Opportunities
    * Meetings
    * Phone Calls
    * Invoices (=invoice.line )
       - group by product_id
    * Contracts (= analytic.account)
    * Timesheets (= partner_id of the analytic account linked to this timesheet)
        - group by date

It allows a salesman to have a direct overlook at all events related to this partner directly from the partner form.
Take care of security rules, add security (read, not write/create/delete) on the group that give access to partners for the objects defined above.
    """, 
    'author': 'Tiny', 
    'website': 'http://www.openerp.com', 
    'depends': ['crm', 'account_analytic_analysis'], 
    'init_xml': [], 
    'update_xml': [
                   'security/ir.model.access.csv', 
                   'partner_crm_view.xml'
                   ], 
    'demo_xml': [], 
    'installable': True, 
    'active': False, 
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
