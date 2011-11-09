# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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
    'name': 'Receive User Feedback',
    'version': '2.0',
    'category': 'Hidden',
    'complexity': "easy",
    'description': """
Add Feedback button in header.
==============================

Invite OpenERP user feedback, powered by uservoice.
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'active': False,
    'certificate': '0040452504963885',

    'js': ['static/src/js/web_uservoice.js'],
    'css': ['static/src/css/uservoice.css'],
    'images': ['static/src/img/submit_an_idea.jpeg', 'static/src/img/web_uservoice_feedback.jpeg'],
}
