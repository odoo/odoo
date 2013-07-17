# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today OpenERP S.A. (<http://openerp.com>).
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
    'name': 'Ideas',
    'summary': 'Share and Discuss your Ideas',
    'version': '1.0',
    'category': 'Tools',
    'description': """
Share your ideas and participate in enterprise innovation
=========================================================

The Ideas module give users a way to express and discuss ideas, allowing everybody
to participate in enterprise innovation. Every user can suggest, comment ideas.
The managers can obtain an easy view of best ideas from all the users.
Once installed, check the menu 'Ideas' in the 'Tools' main menu.""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['mail'],
    'data': [
        'security/idea.xml',
        'security/ir.model.access.csv',
        'views/idea.xml',
        'views/category.xml',
        'data/idea.xml',
        'data/idea_workflow.xml',
    ],
    'demo': [
        'demo/idea.xml',
    ],
    'installable': True,
    'application': True,
    'images': [],
    'css': [
        'static/src/css/idea_idea.css',
    ],
    'js': [],
    'qweb': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
