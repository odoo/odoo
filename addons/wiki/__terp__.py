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
    'name': 'Document Management - Wiki',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'description': """
    The base module to manage documents(wiki) 
    
    keep track for the wiki groups, pages, and history
    """,
    'author': 'Tiny & Axelor',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [
        'wiki_view.xml',
        'data/wiki_quickstart.xml',
        'data/wiki_main.xml',
        'wizard/wizard_view.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': ['data/wiki_faq.xml'],
    'installable': True,
    'active': False,
    'certificate': '0086363630317',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
