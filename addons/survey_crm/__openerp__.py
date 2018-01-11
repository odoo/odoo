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
    'name': 'Survey CRM',
    'version': '2.0',
    'category': 'Marketing',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/page/survey',
    'description': """
Survey - CRM (bridge module)
=================================================================================
This module adds a Survey mass mailing button inside the more option of lead/customers views
""",
    'author': 'OpenERP SA',
    'depends': ['crm', 'survey'],
    'data': [
        'crm_view.xml',
    ],
    'installable': True,
    'auto_install': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
