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
    'name'      : 'Analytic Account View',
    'version'   : '1.1',
    'category'  : 'Finance',
    'description': """
This module is for modifying account analytic view to show important data to project manager of services companies.
===================================================================================================================

Adds menu to show relevant information to each manager.
You can also view the report of account analytic summary
user-wise as well as month wise.
""",
    "author"    : "Camptocamp",
    "website"   : "http://www.camptocamp.com/",
    "images"   : ["images/bill_tasks_works.jpeg","images/overpassed_accounts.jpeg"],
    "depends"   : ["hr_timesheet_invoice"],
    "init_xml"  : [],
    "update_xml": [
                    "security/ir.model.access.csv",
                    "account_analytic_analysis_view.xml",
                    "account_analytic_analysis_menu.xml",
                    ],
    'demo_xml'  : [],
    'installable': True,
    'active'    : False,
    'certificate': '0042927202589',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
