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
    'name': 'Purchase Management - Manual Control of Invoice',
    'version': '1.1',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """Module for purchase management, manual control of invoice""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['purchase'],
    'init_xml': [],
    'update_xml': [
        'purchase_manual_view.xml',
        'purchase_manual_wizard.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
#    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
