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
    'name': 'Document Management - Wiki - FAQ',
    'version': '1.0',
    'category': 'Tools',
    'description': """
    This module provides a Wiki FAQ Template.
    =========================================
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['wiki'],
    'init_xml': [],
    'update_xml': ['wiki_faq.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate' : '00475023941677743389',
    'images': ['images/wiki_groups_internal_faq.jpeg','images/wiki_pages_internal_faq.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
