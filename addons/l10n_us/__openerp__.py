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
    'name': 'United States - Chart of accounts',
    'version': '1.1',
    'author': 'OpenERP SA',
    'category': 'Localization/Account Charts',
    'description': """
United States - Chart of accounts.
    """,
    'website': 'http://www.openerp.com',
    'data': [],
    'depends': [
        'account_chart',
        ],
    'data': [
        'l10n_us_account_type.xml',
        'account_chart_template.xml',
        'account.account.template.csv',
        'account_tax_code_template.xml',
        'account_tax_template.xml',
        'account_chart_template_after.xml',
        'l10n_us_wizard.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
