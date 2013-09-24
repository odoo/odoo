# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Online Events',
    'category': 'Website',
    'summary': 'Schedule, Promote and Sell Events',
    'version': '1.0',
    'description': """
Online Events
=============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'website_mail', 'event_sale', 'website_sale'],
    'data': [
        'event_data.xml',
        'views/website_event.xml',
        'security/ir.model.access.csv',
        'security/website_event.xml',
        'event_demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [],
    'installable': True,
}
