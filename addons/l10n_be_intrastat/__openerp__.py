# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (C) 2014-2015 Odoo S.A. <http://www.odoo.com>
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Belgian Intrastat Declaration',
    'version': '1.0',
    'category': 'Reporting',
    'description': """
Generates Intrastat XML report for declaration
Based on invoices.
    """,
    'author': 'Odoo SA',
    'depends': ['report_intrastat', 'sale_stock', 'account_accountant', 'l10n_be'],
    'data': [
        'data/regions.xml',
        'data/report.intrastat.code.csv',
        'data/transaction.codes.xml',
        'data/transport.modes.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'l10n_be_intrastat.xml',
        'wizard/l10n_be_intrastat_xml_view.xml',
    ],
    'installable': True,
}
