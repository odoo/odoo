# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Account Date check',
    'version': '1.0',
    'category': 'Generic Modules/Accounting',
    'description': """
    * Adds a field on journals: "Allows date not in the period"
    * By default, this field is checked.

If this field is not checked, the system control that the date is in the
period when you create an account entry. Otherwise, it generates an
error message: "The date of your account move is not in the defined
period !"
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['account'],
    'init_xml': [],
    'update_xml': ['account_date_check_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0066174843389',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
