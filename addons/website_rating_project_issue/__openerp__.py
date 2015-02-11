# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Website Rating Project Issue',
    'version': '0.1',
    'category': 'Website',
    'complexity': 'easy',
    'description': """
This module display project customer satisfaction on your website.
==================================================================================================
    """,
    'author': 'Odoo SA',
    'depends': [
        'website_project_issue',
        'rating_project_issue'
    ],
    'data': [
        'views/website_rating_project.xml'
    ],
    'installable': True,
}
