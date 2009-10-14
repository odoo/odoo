# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'report_account_analytic',
    'version': '1.0',
    'category': 'Generic Modules/Accounting',
    'description': """Modify account analytic view to show
important data for project manager of services companies.
Add menu to show relevant information for each manager.""",
    "version" : "1.1",
    "author" : "Camptocamp",
    "category" : "Generic Modules/Accounting",
    "module": "",
    "website": "http://www.camptocamp.com/",
    "depends" : ["account","hr_timesheet","hr_timesheet_invoice","project"],
    "init_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "account_analytic_analysis_view.xml",
        "account_analytic_analysis_menu.xml",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0042927202589',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
