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
    'name': 'Check Writing',
    'version': '1.1',
    'author': 'OpenERP SA, NovaPoint Group',
    'category': 'Generic Modules/Accounting',
    'description': """
Module for the Check Writing and Check Printing.
================================================
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends' : ['account_voucher'],
    'data': [
        'wizard/account_check_batch_printing_view.xml',
        'account_view.xml',
        'account_voucher_view.xml',
        'account_check_writing_data.xml',
        'data/report_paperformat.xml',
        'views/report_check.xml',
        'account_check_writing_report.xml',
    ],
    'demo': ['account_demo.xml'],
    'test': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
