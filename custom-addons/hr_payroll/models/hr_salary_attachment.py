# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import start_of
from odoo.tools.misc import formatLang

from dateutil.relativedelta import relativedelta
from math import ceil


class HrSalaryAttachment(models.Model):
    _name = 'hr.salary.attachment'
    _description = 'Salary Attachment'
    _inherit = ['mail.thread']
    _rec_name = 'description'

    _sql_constraints = [
        (
            'check_monthly_amount', 'CHECK (monthly_amount > 0)',
            'Monthly amount must be strictly positive.'
        ),
        (
            'check_total_amount',
            'CHECK ((total_amount > 0 AND total_amount >= monthly_amount) OR no_end_date = True)',
            'Total amount must be strictly positive and greater than or equal to the monthly amount.'
        ),
        ('check_remaining_amount', 'CHECK (remaining_amount >= 0)', 'Remaining amount must be positive.'),
        ('check_dates', 'CHECK (date_start <= date_end)', 'End date may not be before the starting date.'),
    ]

    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    employee_count = fields.Integer(compute='_compute_employee_count')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    description = fields.Char(required=True)
    deduction_type_id = fields.Many2one(
        'hr.salary.attachment.type',
        string='Type',
        required=True,
        tracking=True,
    )
    no_end_date = fields.Boolean(related='deduction_type_id.no_end_date', store=True)
    monthly_amount = fields.Monetary('Monthly Amount', required=True, tracking=True, help='Amount to pay each month.')
    active_amount = fields.Monetary(
        'Active Amount', compute='_compute_active_amount',
        help='Amount to pay for this month, Monthly Amount or less depending on the Remaining Amount.',
    )
    total_amount = fields.Monetary(
        'Total Amount',
        tracking=True,
        help='Total amount to be paid.',
    )
    has_total_amount = fields.Boolean('Has Total Amount', compute='_compute_has_total_amount')
    paid_amount = fields.Monetary('Paid Amount', tracking=True)
    remaining_amount = fields.Monetary(
        'Remaining Amount', compute='_compute_remaining_amount', store=True,
        help='Remaining amount to be paid.',
    )
    date_start = fields.Date('Start Date', required=True, default=lambda r: start_of(fields.Date.today(), 'month'), tracking=True)
    date_estimated_end = fields.Date(
        'Estimated End Date', compute='_compute_estimated_end',
        help='Approximated end date.',
    )
    date_end = fields.Date(
        'End Date', default=False, tracking=True,
        help='Date at which this assignment has been set as completed or cancelled.',
    )
    state = fields.Selection(
        selection=[
            ('open', 'Running'),
            ('close', 'Completed'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='open',
        required=True,
        tracking=True,
        copy=False,
    )
    payslip_ids = fields.Many2many('hr.payslip', relation='hr_payslip_hr_salary_attachment_rel', string='Payslips', copy=False)
    payslip_count = fields.Integer('# Payslips', compute='_compute_payslip_count')

    attachment = fields.Binary('Document', copy=False)
    attachment_name = fields.Char()

    has_similar_attachment = fields.Boolean(compute='_compute_has_similar_attachment')
    has_similar_attachment_warning = fields.Char(compute='_compute_has_similar_attachment')

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for attachment in self:
            attachment.employee_count = len(attachment.employee_ids)

    @api.depends('monthly_amount', 'date_start', 'date_end')
    def _compute_total_amount(self):
        for record in self:
            if record.has_total_amount:
                date_start = record.date_start if record.date_start else fields.Date.today()
                date_end = record.date_end if record.date_end else fields.Date.today()
                month_difference = (date_end.year - date_start.year) * 12 + (date_end.month - date_start.month)
                record.total_amount = max(0, month_difference + 1) * record.monthly_amount
            else:
                record.total_amount = record.paid_amount

    @api.depends('deduction_type_id', 'date_end')
    def _compute_has_total_amount(self):
        for record in self:
            if record.no_end_date and not record.date_end:
                record.has_total_amount = False
            else:
                record.has_total_amount = True

    @api.depends('total_amount', 'paid_amount', 'monthly_amount')
    def _compute_remaining_amount(self):
        for record in self:
            if record.has_total_amount:
                record.remaining_amount = max(0, record.total_amount - record.paid_amount)
            else:
                record.remaining_amount = record.monthly_amount

    @api.depends('state', 'total_amount', 'monthly_amount', 'date_start')
    def _compute_estimated_end(self):
        for record in self:
            if record.state not in ['close', 'cancel'] and record.has_total_amount and record.monthly_amount:
                record.date_estimated_end = start_of(record.date_start + relativedelta(months=ceil(record.remaining_amount / record.monthly_amount)), 'month')
            else:
                record.date_estimated_end = False

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        for record in self:
            record.payslip_count = len(record.payslip_ids)

    @api.depends('total_amount', 'paid_amount', 'monthly_amount')
    def _compute_active_amount(self):
        for record in self:
            record.active_amount = min(record.monthly_amount, record.remaining_amount)

    @api.depends('employee_ids', 'description', 'monthly_amount', 'date_start')
    def _compute_has_similar_attachment(self):
        date_min = min(self.mapped('date_start'))
        possible_matches = self.search([
            ('state', '=', 'open'),
            ('employee_ids', 'in', self.employee_ids.ids),
            ('monthly_amount', 'in', self.mapped('monthly_amount')),
            ('date_start', '<=', date_min),
        ])
        for record in self:
            similar = []
            if record.employee_count == 1 and record.date_start and record.state == 'open':
                similar = possible_matches.filtered_domain([
                    ('id', '!=', record.id),
                    ('employee_ids', 'in', record.employee_ids.ids),
                    ('monthly_amount', '=', record.monthly_amount),
                    ('date_start', '<=', record.date_start),
                    ('deduction_type_id', '=', record.deduction_type_id.id),
                ])
                similar = similar.filtered(lambda s: s.employee_count == 1)
            record.has_similar_attachment = similar if record.state == 'open' else False
            record.has_similar_attachment_warning = similar and _('Warning, a similar attachment has been found.')

    def action_done(self):
        self.ensure_one()
        if self.employee_count > 1:
            description = self.description
            self.env['hr.salary.attachment'].create([{
                'employee_ids': [(4, employee.id)],
                'company_id': self.company_id.id,
                'description': self.description,
                'deduction_type_id': self.deduction_type_id.id,
                'monthly_amount': self.monthly_amount,
                'total_amount': self.total_amount,
                'paid_amount': self.paid_amount,
                'date_start': self.date_start,
                'date_end': self.date_end,
                'state': 'open',
                'attachment': self.attachment,
                'attachment_name': self.attachment_name,
            } for employee in self.employee_ids])
            self.write({'state': 'close'})
            self.unlink()
            return {
                'type': 'ir.actions.act_window',
                'name': _('Salary Attachments'),
                'res_model': 'hr.salary.attachment',
                'view_mode': 'tree,form',
                'context': {'search_default_description': description},
            }
        self.write({
            'state': 'close',
            'date_end': fields.Date.today(),
        })

    def action_open(self):
        self.ensure_one()
        self.write({
            'state': 'open',
            'date_end': False,
        })

    def action_cancel(self):
        self.ensure_one()
        self.write({
            'state': 'cancel',
            'date_end': fields.Date.today(),
        })

    def action_open_payslips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslips'),
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.payslip_ids.ids)],
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_running(self):
        if any(assignment.state == 'open' for assignment in self):
            raise UserError(_('You cannot delete a running salary attachment!'))

    def record_payment(self, total_amount):
        ''' Record a new payment for this attachment, if the total has been reached the attachment will be closed.

        :param amount: amount to register for this payment
            computed using the monthly_amount and the total if not given

        Note that paid_amount can never be higher than total_amount
        '''
        def _record_payment(attachment, amount):
            attachment.message_post(
                body=_('Recorded a new payment of %s.', formatLang(self.env, amount, currency_obj=attachment.currency_id))
            )
            attachment.paid_amount += amount
            if attachment.remaining_amount == 0:
                attachment.action_done()

        if any(len(a.employee_ids) > 1 for a in self):
            raise UserError(_('You cannot record a payment on multi employees attachments.'))

        remaining = total_amount
        # It is necessary to sort attachments to pay monthly payments (child_support) first
        attachments_sorted = self.sorted(key=lambda a: a.has_total_amount)
        # For all types of attachments, we must pay the monthly_amount without exceeding the total amount
        for attachment in attachments_sorted:
            amount = min(attachment.monthly_amount, attachment.remaining_amount, remaining)
            if not amount:
                continue
            remaining -= amount
            _record_payment(attachment, amount)
        # If we still have remaining, balance the attachments (running) that have a total amount
        # in the chronology of estimated end dates.
        if remaining:
            fixed_total_attachments = self.filtered(lambda a: a.state == 'open' and a.has_total_amount)
            fixed_total_attachments_sorted = fixed_total_attachments.sorted(lambda a: a.date_estimated_end)
            for attachment in fixed_total_attachments_sorted:
                amount = min(attachment.remaining_amount, attachment.remaining_amount, remaining)
                if not amount:
                    continue
                remaining -= amount
                _record_payment(attachment, amount)

    def _get_active_amount(self):
        return sum(self.mapped('active_amount'))
