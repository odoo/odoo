# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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
    'name' : "Portal",
    'version' : "1.0",
    'depends' : ["portal_customer", "crm"],
    'author' : "OpenERP SA",
    'category': 'Portal',
    'description': """
This module defines 'portals' to customize the access to your OpenERP database
for external users.

A portal_customer_lead will show the own leads of the customer.
    """,
    'website': 'http://www.openerp.com',
  
    'update_xml': [
        'portal_customer_lead_data.xml',
        'portal_customer_lead_view.xml',
      
#        'security/ir.model.access.csv',
            ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
