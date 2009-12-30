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
    'name': 'EMail Gateway',
    'version': '1.0',
    'category': 'Generic Modules/Mail Gate',
    'description': """The generic email gateway system for the synchronisation interface
between mails and Open ERP.
""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'process'],
    'init_xml': [],
    'update_xml': [
        'mailgateway_wizard.xml',        
        'mailgateway_view.xml',                
        'security/ir.model.access.csv',        
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': None,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
