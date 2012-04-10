# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from osv import fields, osv
from lxml import etree

class human_resources_configuration(osv.osv_memory):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_hr_timesheet_sheet': fields.boolean('Manage Timesheet and Attendances',
                           help ="""It installs the hr_timesheet_sheet module."""),
        'module_hr_holidays': fields.boolean('Manage Holidays',
                           help ="""It installs the hr_holidays module."""),
        'module_hr_expense': fields.boolean('Manage Employees Expenses',
                           help ="""It installs the hr_expense module."""),
        'module_hr_recruitment': fields.boolean('Manage Recruitment Process',
                           help ="""It installs the hr_payroll module."""),
        'module_hr_contract': fields.boolean('Manage Employees Contracts',
                           help ="""It installs the hr_contract module."""),
        'module_hr_evaluation': fields.boolean('Manage Appraisals Process',
                           help ="""It installs the hr_evaluation module."""),
                }

human_resources_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
