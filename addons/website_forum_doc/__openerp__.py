# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Documentation',
    'category': 'Website',
    'summary': 'Forum, Documentation',
    'version': '1.0',
    'description': """
Documentation based on question and pertinent answers of Forum
        """,
    'author': 'OpenERP SA',
    'depends': [
        'website_forum'
    ],
    'data': [
        'data/doc_data.xml',
        'security/ir.model.access.csv',
        'views/doc.xml',
        'views/website_doc.xml',
    ],
    'demo': [
        'data/doc_demo.xml',
    ],
    'installable': True,
}
