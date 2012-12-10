# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

{
    'name': 'saas_demo',
    'category': 'Hidden',
    'description': """Add a red bar on the top with the following sentence:
"This is a demo version, you can subscribe to use online, browse all apps or back to the website."
And add a new button in the right of the menu: "Sign Up"
""",
    'version': '1.0',
    "depends": [
        'account_accountant',
        'account_analytic_analysis',
        'account_asset',
        'account_voucher',
        'crm',
        'fleet',
        'hr_contract',
        'hr_expense',
        'hr_holidays',
        'hr_recruitment',
        'hr_timesheet_invoice',
        'hr_timesheet_sheet',
        'lunch',
        'mrp',
        'mrp_jit',
        'note',
        'pad',
        'point_of_sale',
        'project_issue',
        'purchase',
        'sale',
        'stock',
        'web',
        'web_analytics',
    ],
    "demo": [
        'setup.xml',
        'demo/en_US.xml',
        'demo/fr_FR.xml',
        'demo/es_ES.xml',
        'demo/zh_CN.xml',
        'demo/de_DE.xml',
        'demo/it_IT.xml',
        'demo/nl_NL.xml',
        'demo/ru_RU.xml',
        'demo/ja_JP.xml',
        'demo/pt_BR.xml',
    ],
    'css': ['static/css/*.css'],
    'qweb': ['static/xml/*.xml'],
    'js': ['static/js/*.js'],
    'auto_install': False,
    'web_preload': False,
}
