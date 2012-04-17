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
  'name' : "Portal Customer claim",
  'version' : "1.0",
  'depends' : ["customer_portal","crm_claim"],
  'author' : "OpenERP SA",
  'category': 'Portal',
  'description': """
   auto_install claim
   """,
   'website': 'http://www.openerp.com',
   'data': [
    ],
   'init_xml' : [
    ],
   'demo_xml' : [.
    ],
   'update_xml' : [
        'claim_custommer_portal_view.xml'
        ],
   'installable': True,
   'auto_install': True,
   #'category': 'Hidden',
}


