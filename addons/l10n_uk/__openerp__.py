# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011 Smartmode LTD (<http://www.smartmode.co.uk>).
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
    'name': 'UK - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the latest UK OpenERP localisation necessary to run OpenERP accounting
for UK SME's with:
    - a CT600-ready chart of accounts
    - VAT100-ready tax structure
    - InfoLogic UK counties listing
    - a few other adaptations""",
    'author': 'SmartMode LTD',
    'website': 'http://www.smartmode.co.uk',
    'depends': ['base_iban', 'base_vat', 'account_chart'],
    'data': [],
    'data': [
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.tax.code.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
        'data/res.country.state.csv',
        'l10n_uk_wizard.xml',
    ],
    'demo' : [
        'demo/demo.xml'
    ],
    'installable': 'True',
    'images': ['images/config_chart_l10n_uk.jpeg','images/l10n_uk_chart.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
