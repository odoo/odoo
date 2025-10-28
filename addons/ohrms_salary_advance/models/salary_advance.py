# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import time
from datetime import datetime
from odoo import exceptions
from odoo.exceptions import UserError
from odoo import api, fields, models, _


class SalaryAdvance(models.Model):
    """Class for the model salary_advance. Contains methods and fields of the
       model."""
    _name = "salary.advance"
    _description = "Salary Advance"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True,
                       default=lambda self: 'Adv/',
                       help='Name of the the advanced salary.')
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  required=True, help="Name of the Employee")
    date = fields.Date(string='Date', required=True,
                       default=lambda self: fields.Date.today(),
                       help="Submit date of the advanced salary.")
    reason = fields.Text(string='Reason', help="Reason for the advance salary"
                                               " request.")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True,
                                  help='Currency of the company.',
                                  default=lambda self: self.env.user.
                                  company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 help='Company of the employee,',
                                 default=lambda self: self.env.user.company_id)
    advance = fields.Float(string='Advance', required=True,
                           help='The requested money.')
    payment_method_id = fields.Many2one('account.journal',
                                        string='Payment Method',
                                        help='Pyment method of the salary'
                                             ' advance.')
    exceed_condition = fields.Boolean(string='Exceed than Maximum',
                                      help="The Advance is greater than the "
                                           "maximum percentage in salary "
                                           "structure")
    department_id = fields.Many2one('hr.department', string='Department',
                                    related='employee_id.department_id',
                                    help='Department of the employee.')
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('waiting_approval', 'Waiting Approval'),
                              ('approve', 'Approved'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Rejected')], string='Status',
                             default='draft', track_visibility='onchange',
                             help='State of the salary advance.')
    debit_id = fields.Many2one('account.account', string='Debit Account',
                               help='Debit account of the salary advance.')
    credit_id = fields.Many2one('account.account', string='Credit Account',
                                help='Credit account of the salary advance.')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 help='Journal of the salary advance.')
    employee_contract_id = fields.Many2one('hr.version', string='Contract',
                                           related='employee_id.version_id',
                                           help='Running contract of the '
                                                'employee.')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """This method will trigger when there is a change in company_id."""
        company = self.company_id
        domain = [('company_id.id', '=', company.id)]
        result = {
            'domain': {
                'journal_id': domain,
            },
        }
        return result

    def action_submit_to_manager(self):
        """Method of a button. Changing the state of the salary advance."""
        self.state = 'submit'

    def action_cancel(self):
        """Method of a button. Changing the state of the salary advance."""
        self.state = 'cancel'

    def action_reject(self):
        """Method of a button. Changing the state of the salary advance."""
        self.state = 'reject'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence for salary advance."""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('salary.advance.seq') or '/'
        records = super(SalaryAdvance, self).create(vals_list)
        return records

    def approve_request(self):
        """This Approves the employee salary advance request."""
        if not self.employee_id.address_id.id:
            raise UserError('Define home address for the employee. i.e address'
                            ' under private information of the employee.')
        salary_advance_search = self.search(
            [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id),
             ('state', '=', 'approve')])
        current_month = datetime.strptime(str(self.date),
                                          '%Y-%m-%d').date().month
        for each_advance in salary_advance_search:
            existing_month = datetime.strptime(str(each_advance.date),
                                               '%Y-%m-%d').date().month
            if current_month == existing_month:
                raise UserError('Advance can be requested once in a month')
        if not self.employee_contract_id:
            raise UserError('Define a contract for the employee')
        if (self.advance > self.employee_contract_id.wage
                and not self.exceed_condition):
            raise UserError('Advance amount is greater than allotted')

        if not self.advance:
            raise UserError('You must Enter the Salary Advance amount')
        payslip_ids = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id),
             ('state', '=', 'done'), ('date_from', '<=', self.date),
             ('date_to', '>=', self.date)])
        if payslip_ids:
            raise UserError("This month salary already calculated")
        for slip in self.env['hr.payslip'].search(
                [('employee_id', '=', self.employee_id.id)]):
            slip_moth = datetime.strptime(str(slip.date_from),
                                          '%Y-%m-%d').date().month
            if current_month == slip_moth + 1:
                slip_day = datetime.strptime(str(slip.date_from),
                                             '%Y-%m-%d').date().day
                current_day = datetime.strptime(str(self.date),
                                                '%Y-%m-%d').date().day
                if (current_day - slip_day < self.
                        employee_contract_id.struct_id.advance_date):
                    raise exceptions.UserError(
                        _('Request can be done after "%s" Days From prevoius'
                          ' month salary') % self.
                        employee_contract_id.struct_id.advance_date)
        self.state = 'waiting_approval'

    def approve_request_acc_dept(self):
        """This Approves the employee salary advance request from accounting
         department."""
        salary_advance_search = self.search(
            [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id),
             ('state', '=', 'approve')])
        current_month = datetime.strptime(str(self.date),
                                          '%Y-%m-%d').date().month
        for each_advance in salary_advance_search:
            existing_month = datetime.strptime(str(each_advance.date),
                                               '%Y-%m-%d').date().month
            if current_month == existing_month:
                raise UserError('Advance can be requested once in a month')
        if not self.debit_id or not self.credit_id or not self.journal_id:
            raise UserError("You must enter Debit & Credit account and"
                            " journal to approve ")
        if not self.advance:
            raise UserError('You must Enter the Salary Advance amount')
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        for request in self:
            move = {
                'narration': 'Salary Advance Of ' + request.employee_id.name,
                'ref': request.name,
                'journal_id': request.journal_id.id,
                'date': time.strftime('%Y-%m-%d'),
            }
            if request.debit_id.id:
                debit_line = (0, 0, {
                    'name': request.employee_id.name,
                    'account_id': request.debit_id.id,
                    'journal_id': request.journal_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'debit': request.advance > 0.0 and request.advance or 0.0,
                    'credit': request.advance < 0.0 and -request.advance or 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            if request.credit_id.id:
                credit_line = (0, 0, {
                    'name': request.employee_id.name,
                    'account_id': request.credit_id.id,
                    'journal_id': request.journal_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'debit': request.advance < 0.0 and -request.advance or 0.0,
                    'credit': request.advance > 0.0 and request.advance or 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2][
                    'debit']
            move.update({'line_ids': line_ids})
            draft = self.env['account.move'].create(move)
            draft.action_post()
            self.state = 'approve'
            return True
