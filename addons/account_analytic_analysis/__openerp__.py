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
    'name': 'Contracts Management',
    'version': '1.1',
    'category': 'Sales Management',
    'description': """
This module is for modifying account analytic view to show important data to project manager of services companies.
===================================================================================================================

Adds menu to show relevant information to each manager.You can also view the report of account analytic summary user-wise as well as month-wise.
""",
    'author': 'Camptocamp / Odoo',
    'website': 'https://www.odoo.com/page/billing',
    'images': ['images/bill_tasks_works.jpeg','images/overpassed_accounts.jpeg'],
    'depends': ['hr_timesheet_invoice', 'sale'], #although sale is technically not required to install this module, all menuitems are located under 'Sales' application
    'data': [
        'security/ir.model.access.csv',
        'security/account_analytic_analysis_security.xml',
        'account_analytic_analysis_view.xml',
        'account_analytic_analysis_cron.xml',
        'res_config_view.xml',
        'views/account_analytic_analysis.xml',
    ],
    'demo': ['analytic_account_demo.xml'],
    'test': ['test/account_analytic_analysis.yml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
