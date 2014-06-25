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
    'name': 'Indian - Accounting',
    'version': '1.0',
    'description': """
Indian Accounting: Chart of Account.
====================================

Indian accounting chart and localization.

OpenERP allows to manage Indian Accounting by providing Two Formats Of Chart of Accounts i.e Indian Chart Of Accounts - Standard and Indian Chart Of Accounts - Schedule VI.

Note: The Schedule VI has been revised by MCA and is applicable for all Balance Sheet made after
31st March, 2011. The Format has done away with earlier two options of format of Balance
Sheet, now only Vertical format has been permitted Which is Supported By OpenERP.
  """,
    'author': ['OpenERP SA'],
    'category': 'Localization/Account Charts',
    'depends': [
        'account',
        'account_chart'
    ],
    'demo': [],
    'data': [
        'l10n_in_tax_code_template.xml',
        'l10n_in_standard_chart.xml',
        'l10n_in_standard_tax_template.xml',
        'l10n_in_schedule6_chart.xml',
        'l10n_in_schedule6_tax_template.xml',
        'l10n_in_wizard.xml',
    ],
    'auto_install': False,
    'installable': True,
    'images': ['images/config_chart_l10n_in.jpeg','images/l10n_in_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
