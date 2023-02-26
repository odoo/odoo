# -*- coding: utf-8 -*-
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Athira Premanand (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from odoo import models, fields, api


class HrAttendanceMultiCompany(models.Model):
    _inherit = 'hr.attendance'

    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)


class HrLeaveMultiCompany(models.Model):
    _inherit = 'hr.leave'

    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id.id)
    @api.onchange('name')
    def dfgb(self):
        print(self.env.user.company_id)





class HrPayslipMultiCompany(models.Model):
    _inherit = 'hr.payslip.run'

    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)


class HrSalaryCategoryMultiCompany(models.Model):
    _inherit = 'hr.salary.rule.category'

    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny",
                                 default=lambda self: self.env.user.company_id)
