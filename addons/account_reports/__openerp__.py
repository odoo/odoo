# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2015 Odoo S.A. <http://www.odoo.com>
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
    'name' : 'Accounting Reports',
    'author' : 'Odoo SA',
    'summary': 'View and create reports',
    'description': """
Accounting Reports
====================
    """,
    'depends': ['account'],
    'data': [
        'data/init.yml',
        'data/account_financial_report_data.xml',
        'views/report_financial.xml',
        'views/report_followup.xml',
        'views/company_view.xml',
        'views/partner_view.xml',
        'views/account_journal_dashboard_view.xml',
    ],
    'qweb': [
        'static/src/xml/account_report_backend.xml',
    ],
    'auto_install': True,
}
