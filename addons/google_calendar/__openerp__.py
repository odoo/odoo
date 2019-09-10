# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Google Calendar',
    'version': '1.0',
    'category': 'Tools',
    'description': """
The module adds the possibility to synchronize Google Calendar with OpenERP
===========================================================================
""",
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['google_account', 'calendar'],
    'qweb': ['static/src/xml/*.xml'],
    'data': [
        'res_config_view.xml',
        'security/ir.model.access.csv',
        'views/google_calendar.xml',
        'views/res_users.xml',
        'google_calendar.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
