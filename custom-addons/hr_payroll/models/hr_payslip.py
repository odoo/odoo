# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import math
import pytz

from collections import defaultdict, Counter
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND
from odoo.tools import float_round, date_utils, convert_file, format_amount
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class DefaultDictPayroll(defaultdict):
    def get(self, key, default=None):
        if key not in self and default is not None:
            self[key] = default
        return self[key]


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread.cc', 'mail.thread.main.attachment', 'mail.activity.mixin']
    _order = 'date_to desc'

    struct_id = fields.Many2one(
        'hr.payroll.structure', string='Structure', precompute=True,
        compute='_compute_struct_id', store=True, readonly=False, tracking=True,
        help='Defines the rules that have to be applied to this payslip, according '
             'to the contract chosen. If the contract is empty, this field isn\'t '
             'mandatory anymore and all the valid rules of the structures '
             'of the employee\'s contracts will be applied.')
    structure_code = fields.Char(related="struct_id.code")
    struct_type_id = fields.Many2one('hr.payroll.structure.type', related='struct_id.type_id')
    wage_type = fields.Selection(related='contract_id.wage_type')
    name = fields.Char(
        string='Payslip Name', required=True,
        compute='_compute_name', store=True, readonly=False)
    number = fields.Char(
        string='Reference', copy=False)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), '|', ('active', '=', True), ('active', '=', False)]")
    image_128 = fields.Image(related='employee_id.image_128')
    image_1920 = fields.Image(related='employee_id.image_1920')
    avatar_128 = fields.Image(related='employee_id.avatar_128')
    avatar_1920 = fields.Image(related='employee_id.avatar_1920')
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id', readonly=True, store=True)
    date_from = fields.Date(
        string='From', readonly=False, required=True, tracking=True,
        compute="_compute_date_from", store=True, precompute=True)
    date_to = fields.Date(
        string='To', readonly=False, required=True, tracking=True,
        compute="_compute_date_to", store=True, precompute=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected')],
        string='Status', index=True, readonly=True, copy=False,
        default='draft', tracking=True,
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', string='Payslip Lines',
        compute='_compute_line_ids', store=True, readonly=False, copy=True)
    company_id = fields.Many2one(
        'res.company', string='Company', copy=False, required=True,
        compute='_compute_company_id', store=True, readonly=False,
        default=lambda self: self.env.company)
    country_id = fields.Many2one(
        'res.country', string='Country',
        related='company_id.country_id', readonly=True
    )
    country_code = fields.Char(related='country_id.code', depends=['country_id'], readonly=True)
    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked_days', 'payslip_id', string='Payslip Worked Days', copy=True,
        compute='_compute_worked_days_line_ids', store=True, readonly=False)
    input_line_ids = fields.One2many(
        'hr.payslip.input', 'payslip_id', string='Payslip Inputs',
        compute='_compute_input_line_ids', store=True,
        readonly=False)
    paid = fields.Boolean(
        string='Made Payment Order? ', copy=False)
    paid_date = fields.Date(string="Close Date", help="The date on which the payment is made to the employee.")
    note = fields.Text(string='Internal Note')
    contract_domain_ids = fields.Many2many('hr.contract', compute='_compute_contract_domain_ids')
    contract_id = fields.Many2one(
        'hr.contract', string='Contract', precompute=True,
        domain="[('id', 'in', contract_domain_ids)]", tracking=True,
        compute='_compute_contract_id', store=True, readonly=False)
    credit_note = fields.Boolean(
        string='Credit Note',
        help="Indicates this payslip has a refund of another")
    has_refund_slip = fields.Boolean(compute='_compute_has_refund_slip')
    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Batch Name',
        copy=False, ondelete='cascade', tracking=True,
        domain="[('company_id', '=', company_id)]")
    sum_worked_hours = fields.Float(compute='_compute_worked_hours', store=True, help='Total hours of attendance and time off (paid or not)')
    compute_date = fields.Date('Computed On')
    basic_wage = fields.Monetary(compute='_compute_basic_net', store=True)
    gross_wage = fields.Monetary(compute='_compute_basic_net', store=True)
    net_wage = fields.Monetary(compute='_compute_basic_net', store=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    warning_message = fields.Char(compute='_compute_warning_message', store=True, readonly=True)
    is_wrong_duration = fields.Boolean(compute='_compute_is_wrong_duration', compute_sudo=True)
    is_regular = fields.Boolean(compute='_compute_is_regular')
    has_negative_net_to_report = fields.Boolean()
    negative_net_to_report_display = fields.Boolean(compute='_compute_negative_net_to_report_display')
    negative_net_to_report_message = fields.Char(compute='_compute_negative_net_to_report_display')
    negative_net_to_report_amount = fields.Float(compute='_compute_negative_net_to_report_display')
    is_superuser = fields.Boolean(compute="_compute_is_superuser")
    edited = fields.Boolean()
    queued_for_pdf = fields.Boolean(default=False)

    salary_attachment_ids = fields.Many2many(
        'hr.salary.attachment',
        relation='hr_payslip_hr_salary_attachment_rel',
        string='Salary Attachments',
        compute='_compute_salary_attachment_ids',
        store=True,
        readonly=False,
    )
    salary_attachment_count = fields.Integer('Salary Attachment count', compute='_compute_salary_attachment_count')
    use_worked_day_lines = fields.Boolean(related="struct_id.use_worked_day_lines")

    def _get_schedule_period_start(self):
        schedule = self.contract_id.schedule_pay or self.contract_id.structure_type_id.default_schedule_pay
        today = date.today()
        week_start = self.env["res.lang"]._lang_get(self.env.user.lang).week_start
        date_from = today

        if schedule == 'quarterly':
            current_year_quarter = math.ceil(today.month / 3)
            date_from = today.replace(day=1, month=(current_year_quarter - 1) * 3 + 1)
        elif schedule == 'semi-annually':
            is_second_half = math.floor((today.month - 1) / 6)
            date_from = today.replace(day=1, month=7) if is_second_half else today.replace(day=1, month=1)
        elif schedule == 'annually':
            date_from = today.replace(day=1, month=1)
        elif schedule == 'weekly':
            week_day = today.weekday()
            date_from = today + relativedelta(days=-week_day)
        elif schedule == 'bi-weekly':
            week = int(today.strftime("%U") if week_start == '7' else today.strftime("%W"))
            week_day = today.weekday()
            is_second_week = week % 2 == 0
            date_from = today + relativedelta(days=-week_day - 7 * int(is_second_week))
        elif schedule == 'bi-monthly':
            current_year_slice = math.ceil(today.month / 2)
            date_from = today.replace(day=1, month=(current_year_slice - 1) * 2 + 1)
        else:  # if not handled, put the monthly behaviour
            date_from = today.replace(day=1)
        if self.contract_id and date_from < self.contract_id.date_start:
            date_from = self.contract_id.date_start
        return date_from

    @api.depends('contract_id', 'struct_id')
    def _compute_date_from(self):
        for payslip in self:
            if self.env.context.get('default_date_from'):
                payslip.date_from = self.env.context.get('default_date_from')
            else:
                payslip.date_from = payslip._get_schedule_period_start()

    def _get_schedule_timedelta(self):
        self.ensure_one()
        schedule = self.contract_id.schedule_pay or self.contract_id.structure_type_id.default_schedule_pay
        if schedule == 'quarterly':
            timedelta = relativedelta(months=3, days=-1)
        elif schedule == 'semi-annually':
            timedelta = relativedelta(months=6, days=-1)
        elif schedule == 'annually':
            timedelta = relativedelta(years=1, days=-1)
        elif schedule == 'weekly':
            timedelta = relativedelta(days=6)
        elif schedule == 'bi-weekly':
            timedelta = relativedelta(days=13)
        elif schedule == 'semi-monthly':
            timedelta = relativedelta(day=15 if self.date_from.day < 15 else 31)
        elif schedule == 'bi-monthly':
            timedelta = relativedelta(months=2, days=-1)
        elif schedule == 'daily':
            timedelta = relativedelta(days=0)
        else:  # if not handled, put the monthly behaviour
            timedelta = relativedelta(months=1, days=-1)
        return timedelta

    @api.depends('date_from', 'contract_id', 'struct_id')
    def _compute_date_to(self):
        for payslip in self:
            if self.env.context.get('default_date_to'):
                payslip.date_to = self.env.context.get('default_date_to')
            else:
                payslip.date_to = payslip.date_from and payslip.date_from + payslip._get_schedule_timedelta()
            if payslip.contract_id and payslip.contract_id.date_end\
                    and payslip.date_from >= payslip.contract_id.date_start\
                    and payslip.date_from < payslip.contract_id.date_end\
                    and payslip.date_to > payslip.contract_id.date_end:
                payslip.date_to = payslip.contract_id.date_end

    @api.depends('company_id', 'employee_id')
    def _compute_contract_domain_ids(self):
        for payslip in self:
            payslip.contract_domain_ids = self.env['hr.contract'].search([
                ('company_id', '=', payslip.company_id.id),
                ('employee_id', '=', payslip.employee_id.id),
                ('state', 'in', ['open', 'close']),
            ])

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'struct_id')
    def _compute_input_line_ids(self):
        attachment_types = self._get_attachment_types()
        attachment_type_ids = [f.id for f in attachment_types.values()]
        for slip in self:
            if not slip.employee_id or not slip.employee_id.salary_attachment_ids or not slip.struct_id:
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id.id in attachment_type_ids)
                slip.update({'input_line_ids': [Command.unlink(line.id) for line in lines_to_remove]})
            if slip.employee_id.salary_attachment_ids and slip.date_to:
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id.id in attachment_type_ids)
                input_line_vals = [Command.unlink(line.id) for line in lines_to_remove]

                valid_attachments = slip.employee_id.salary_attachment_ids.filtered(
                    lambda a: a.state == 'open'
                        and a.date_start <= slip.date_to
                        and (not a.date_end or a.date_end >= slip.date_from)
                )
                # Only take deduction types present in structure
                deduction_types = list(set(valid_attachments.deduction_type_id.mapped('code')))
                struct_deduction_lines = list(set(slip.struct_id.rule_ids.mapped('code')))
                included_deduction_types = [f for f in deduction_types if attachment_types[f].code in struct_deduction_lines]
                for deduction_type in included_deduction_types:
                    if not slip.struct_id.rule_ids.filtered(lambda r: r.active and r.code == attachment_types[deduction_type].code):
                        continue
                    attachments = valid_attachments.filtered(lambda a: a.deduction_type_id.code == deduction_type)
                    amount = attachments._get_active_amount()
                    name = ', '.join(attachments.mapped('description'))
                    input_type_id = attachment_types[deduction_type].id
                    input_line_vals.append(Command.create({
                        'name': name,
                        'amount': amount if not slip.credit_note else -amount,
                        'input_type_id': input_type_id,
                    }))
                slip.update({'input_line_ids': input_line_vals})

    @api.depends('input_line_ids.input_type_id', 'input_line_ids')
    def _compute_salary_attachment_ids(self):
        attachment_types = self._get_attachment_types()
        for slip in self:
            if not slip.input_line_ids and not slip.salary_attachment_ids:
                continue
            attachments = self.env['hr.salary.attachment']
            if slip.employee_id and slip.input_line_ids and slip.date_to:
                input_line_type_ids = slip.input_line_ids.mapped('input_type_id.id')
                deduction_types = [f for f in attachment_types if attachment_types[f].id in input_line_type_ids]
                attachments = slip.employee_id.salary_attachment_ids.filtered(
                    lambda a: (
                        a.state == 'open'
                        and a.deduction_type_id.code in deduction_types
                        and a.date_start <= slip.date_to
                    )
                )
            slip.salary_attachment_ids = attachments

    @api.depends('salary_attachment_ids')
    def _compute_salary_attachment_count(self):
        for slip in self:
            slip.salary_attachment_count = len(slip.salary_attachment_ids)

    @api.depends('employee_id', 'state')
    def _compute_negative_net_to_report_display(self):
        activity_type = self.env.ref('hr_payroll.mail_activity_data_hr_payslip_negative_net')
        for payslip in self:
            if payslip.state in ['draft', 'verify']:
                payslips_to_report = self.env['hr.payslip'].search([
                    ('has_negative_net_to_report', '=', True),
                    ('employee_id', '=', payslip.employee_id.id),
                    ('credit_note', '=', False),
                ])
                payslip.negative_net_to_report_display = payslips_to_report
                payslip.negative_net_to_report_amount = payslips_to_report._get_line_values(['NET'], compute_sum=True)['NET']['sum']['total']
                payslip.negative_net_to_report_message = _(
                    'Note: There are previous payslips with a negative amount for a total of %s to report.',
                    round(payslip.negative_net_to_report_amount, 2))
                if payslips_to_report and payslip.state == 'verify' and payslip.contract_id and not payslip.activity_ids.filtered(lambda a: a.activity_type_id == activity_type):
                    payslip.activity_schedule(
                        'hr_payroll.mail_activity_data_hr_payslip_negative_net',
                        summary=_('Previous Negative Payslip to Report'),
                        note=_('At least one previous negative net could be reported on this payslip for %s',
                                payslip.employee_id._get_html_link()),
                        user_id=payslip.contract_id.hr_responsible_id.id or self.env.ref('base.user_admin').id)
            else:
                payslip.negative_net_to_report_display = False
                payslip.negative_net_to_report_amount = False
                payslip.negative_net_to_report_message = False

    def _get_negative_net_input_type(self):
        self.ensure_one()
        return self.env.ref('hr_payroll.input_deduction')

    def action_report_negative_amount(self):
        self.ensure_one()
        deduction_input_type = self._get_negative_net_input_type()
        deduction_input_line = self.input_line_ids.filtered(lambda l: l.input_type_id == deduction_input_type)
        if deduction_input_line:
            deduction_input_line.amount += abs(self.negative_net_to_report_amount)
        else:
            self.write({'input_line_ids': [(0, 0, {
                'input_type_id': deduction_input_type.id,
                'amount': abs(self.negative_net_to_report_amount),
            })]})
            self.compute_sheet()
        self.env['hr.payslip'].search([
            ('has_negative_net_to_report', '=', True),
            ('employee_id', '=', self.employee_id.id),
            ('credit_note', '=', False),
        ]).write({'has_negative_net_to_report': False})
        self.activity_feedback(['hr_payroll.mail_activity_data_hr_payslip_negative_net'])

    def _compute_is_regular(self):
        for payslip in self:
            payslip.is_regular = payslip.struct_id.type_id.default_struct_id == payslip.struct_id

    def _is_invalid(self):
        self.ensure_one()
        if self.state not in ['done', 'paid']:
            return _("This payslip is not validated. This is not a legal document.")
        return False

    @api.depends('worked_days_line_ids', 'input_line_ids')
    def _compute_line_ids(self):
        if not self.env.context.get("payslip_no_recompute"):
            return
        payslips = self.filtered(lambda p: p.line_ids and p.state in ['draft', 'verify'])
        payslips.line_ids.unlink()
        self.env['hr.payslip.line'].create(payslips._get_payslip_lines())

    @api.depends('line_ids.total')
    def _compute_basic_net(self):
        line_values = (self._origin)._get_line_values(['BASIC', 'GROSS', 'NET'])
        for payslip in self:
            payslip.basic_wage = line_values['BASIC'][payslip._origin.id]['total']
            payslip.gross_wage = line_values['GROSS'][payslip._origin.id]['total']
            payslip.net_wage = line_values['NET'][payslip._origin.id]['total']

    @api.depends('worked_days_line_ids.number_of_hours', 'worked_days_line_ids.is_paid', 'worked_days_line_ids.is_credit_time')
    def _compute_worked_hours(self):
        for payslip in self:
            payslip.sum_worked_hours = sum([line.number_of_hours for line in payslip.worked_days_line_ids if not line.is_credit_time])

    def _compute_is_superuser(self):
        self.update({'is_superuser': self.env.user._is_superuser() and self.user_has_groups("base.group_no_one")})

    def _compute_has_refund_slip(self):
        # This field is only used to know whether we need a confirm on refund or not
        # It doesn't have to work in batch and we try not to search if not necessary
        for payslip in self:
            if not payslip.credit_note and payslip.state in ('done', 'paid') and self.search_count([
                ('employee_id', '=', payslip.employee_id.id),
                ('date_from', '=', payslip.date_from),
                ('date_to', '=', payslip.date_to),
                ('contract_id', '=', payslip.contract_id.id),
                ('struct_id', '=', payslip.struct_id.id),
                ('credit_note', '=', True),
                ('state', '!=', 'cancel'),
                ]):
                payslip.has_refund_slip = True
            else:
                payslip.has_refund_slip = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(payslip.date_from > payslip.date_to for payslip in self):
            raise ValidationError(_("Payslip 'Date From' must be earlier than 'Date To'."))

    def _record_attachment_payment(self, attachments, slip_lines):
        self.ensure_one()
        if self.credit_note:
            attachments.record_payment(-abs(slip_lines.total))
        else:
            attachments.record_payment(abs(slip_lines.total))

    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals and vals['state'] == 'paid':
            # Register payment in Salary Attachments
            # NOTE: Since we combine multiple attachments on one input line, it's not possible to compute
            #  how much per attachment needs to be taken record_payment will consume monthly payments (child_support) before other attachments
            attachment_types = self._get_attachment_types()
            for slip in self.filtered(lambda r: r.salary_attachment_ids):
                for deduction_type, input_type_id in attachment_types.items():
                    attachments = slip.salary_attachment_ids.filtered(lambda r: r.deduction_type_id.code == deduction_type)
                    input_lines = slip.input_line_ids.filtered(lambda r: r.input_type_id.id == input_type_id.id)
                    # Use the amount from the computed value in the payslip lines not the input
                    salary_lines = slip.line_ids.filtered(lambda r: r.code in input_lines.mapped('code'))
                    if not attachments or not salary_lines:
                        continue
                    slip._record_attachment_payment(attachments, salary_lines)
        return res

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def _get_pdf_reports(self):
        classic_report = self.env.ref('hr_payroll.action_report_payslip')
        result = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                result[classic_report] |= payslip
            else:
                result[payslip.struct_id.report_id] |= payslip
        return result

    @api.model
    def _get_email_template(self):
        return self.env.ref(
            'hr_payroll.mail_template_new_payslip', raise_if_not_found=False
        )

    def _generate_pdf(self):
        mapped_reports = self._get_pdf_reports()
        attachments_vals_list = []
        generic_name = _("Payslip")
        template = self._get_email_template()
        for report, payslips in mapped_reports.items():
            for payslip in payslips:
                pdf_content, dummy = self.env['ir.actions.report'].sudo().with_context(lang=payslip.employee_id.lang or self.env.lang)._render_qweb_pdf(report, payslip.id)
                if report.print_report_name:
                    pdf_name = safe_eval(report.print_report_name, {'object': payslip})
                else:
                    pdf_name = generic_name
                attachments_vals_list.append({
                    'name': pdf_name,
                    'type': 'binary',
                    'raw': pdf_content,
                    'res_model': payslip._name,
                    'res_id': payslip.id
                })
                # Send email to employees
                if template:
                    template.send_mail(payslip.id, email_layout_xmlid='mail.mail_notification_light')
        self.env['ir.attachment'].sudo().create(attachments_vals_list)

    def _filter_out_of_contracts_payslips(self):
        return self.filtered(lambda p: p.contract_id and (p.contract_id.date_start > p.date_to or (p.contract_id.date_end and p.contract_id.date_end < p.date_from)))

    def action_payslip_done(self):
        invalid_payslips = self._filter_out_of_contracts_payslips()
        if invalid_payslips:
            raise ValidationError(_('The following employees have a contract outside of the payslip period:\n%s', '\n'.join(invalid_payslips.mapped('employee_id.name'))))
        if any(slip.contract_id.state == 'cancel' for slip in self):
            raise ValidationError(_('You cannot validate a payslip on which the contract is cancelled'))
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled payslip."))
        self.write({'state' : 'done'})

        line_values = self._get_line_values(['NET'])

        self.filtered(lambda p: not p.credit_note and line_values['NET'][p.id]['total'] < 0).write({'has_negative_net_to_report': True})
        self.mapped('payslip_run_id').action_close()
        # Validate work entries for regular payslips (exclude end of year bonus, ...)
        regular_payslips = self.filtered(lambda p: p.struct_id.type_id.default_struct_id == p.struct_id)
        work_entries = self.env['hr.work.entry']
        for regular_payslip in regular_payslips:
            work_entries |= self.env['hr.work.entry'].search([
                ('date_start', '<=', regular_payslip.date_to),
                ('date_stop', '>=', regular_payslip.date_from),
                ('employee_id', '=', regular_payslip.employee_id.id),
            ])
        if work_entries:
            work_entries.action_validate()

        if self.env.context.get('payslip_generate_pdf'):
            if self.env.context.get('payslip_generate_pdf_direct'):
                self._generate_pdf()
            else:
                self.write({'queued_for_pdf': True})
                payslip_cron = self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs', raise_if_not_found=False)
                if payslip_cron:
                    payslip_cron._trigger()

    def action_payslip_cancel(self):
        if not self.env.user._is_system() and self.filtered(lambda slip: slip.state == 'done'):
            raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        self.mapped('payslip_run_id').action_close()

    def action_payslip_paid(self):
        if any(slip.state != 'done' for slip in self):
            raise UserError(_('Cannot mark payslip as paid if not confirmed.'))
        self.write({
            'state': 'paid',
            'paid_date': fields.Date.today(),
        })

    def action_open_work_entries(self):
        self.ensure_one()
        return self.employee_id.action_open_work_entries(initial_date=self.date_from)

    def action_open_salary_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Salary Attachments'),
            'res_model': 'hr.salary.attachment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.salary_attachment_ids.ids)],
        }

    def refund_sheet(self):
        copied_payslips = self.env['hr.payslip']
        for payslip in self:
            copied_payslip = payslip.copy({
                'credit_note': True,
                'name': _('Refund: %(payslip)s', payslip=payslip.name),
                'edited': True,
                'state': 'verify',
            })
            for wd in copied_payslip.worked_days_line_ids:
                wd.number_of_hours = -wd.number_of_hours
                wd.number_of_days = -wd.number_of_days
                wd.amount = -wd.amount
            for line in copied_payslip.line_ids:
                line.amount = -line.amount
                line.total = -line.total
            copied_payslips |= copied_payslip
        formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', copied_payslips.ids)],
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(payslip.state not in ('draft', 'cancel') for payslip in self):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))

    def compute_sheet(self):
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'])
        # delete old payslip lines
        payslips.line_ids.unlink()
        # this guarantees consistent results
        self.env.flush_all()
        today = fields.Date.today()
        for payslip in payslips:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            payslip.write({
                'number': number,
                'state': 'verify',
                'compute_date': today
            })
        self.env['hr.payslip.line'].create(payslips._get_payslip_lines())
        return True

    def action_refresh_from_work_entries(self):
        # Refresh the whole payslip in case the HR has modified some work entries
        # after the payslip generation
        if any(p.state not in ['draft', 'verify'] for p in self):
            raise UserError(_('The payslips should be in Draft or Waiting state.'))
        payslips = self.filtered(lambda p: not p.edited)
        payslips.mapped('worked_days_line_ids').unlink()
        payslips.mapped('line_ids').unlink()
        payslips._compute_worked_days_line_ids()
        payslips.compute_sheet()

    def _round_days(self, work_entry_type, days):
        if work_entry_type.round_days != 'NO':
            precision_rounding = 0.5 if work_entry_type.round_days == "HALF" else 1
            day_rounded = float_round(days, precision_rounding=precision_rounding, rounding_method=work_entry_type.round_days_type)
            return day_rounded
        return days

    @api.model
    def _get_attachment_types(self):
        attachment_types = self.env['hr.salary.attachment.type'].search([])
        input_types = self.env['hr.payslip.input.type'].search([('code', 'in', attachment_types.mapped('code'))])
        missing_input_types = list(set(attachment_types.mapped('code')) - set(input_types.mapped('code')))
        if missing_input_types:
            raise UserError(_("No Other Input Type was found for the following Salary Attachment Types codes:\n%s", '\n'.join(missing_input_types)))
        result = {}
        for attachment_type in attachment_types:
            for input_type in input_types:
                if input_type.code == attachment_type.code:
                    result[attachment_type.code] = input_type
                    break
        return result

    def _get_worked_day_lines_hours_per_day(self):
        self.ensure_one()
        return self.contract_id.resource_calendar_id.hours_per_day

    def _get_out_of_contract_calendar(self):
        self.ensure_one()
        if self.contract_id.time_credit:
            return self.contract_id.standard_calendar_id
        return self.contract_id.resource_calendar_id

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        hours_per_day = self._get_worked_day_lines_hours_per_day()
        work_hours = self.contract_id.get_work_hours(self.date_from, self.date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_days_rounding = 0
        for work_entry_type_id, hours in work_hours_ordered:
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
            }
            res.append(attendance_line)

        # Sort by Work Entry Type sequence
        work_entry_type = self.env['hr.work.entry.type']
        return sorted(res, key=lambda d: work_entry_type.browse(d['work_entry_type_id']).sequence)

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        if contract.resource_calendar_id:
            res = self._get_worked_day_lines_values(domain=domain)
            if not check_out_of_contract:
                return res

            # If the contract doesn't cover the whole month, create
            # worked_days lines to adapt the wage accordingly
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']

            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                res.append({
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': out_days,
                    'number_of_hours': out_hours,
                })
        return res

    @property
    def paid_amount(self):
        self.ensure_one()
        return self._get_paid_amount()

    @property
    def is_outside_contract(self):
        self.ensure_one()
        return self._is_outside_contract_dates()

    def _rule_parameter(self, code):
        self.ensure_one()
        return self.env['hr.rule.parameter']._get_parameter_from_code(code, self.date_to)

    def _sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""
            SELECT sum(pl.total)
            FROM hr_payslip as hp, hr_payslip_line as pl
            WHERE hp.employee_id = %s
            AND hp.state in ('done', 'paid')
            AND hp.date_from >= %s
            AND hp.date_to <= %s
            AND hp.id = pl.slip_id
            AND pl.code = %s""", (self.employee_id.id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0

    def _sum_category(self, code, from_date, to_date=None):
        self.ensure_one()
        if to_date is None:
            to_date = fields.Date.today()

        self.env['hr.payslip'].flush_model(['employee_id', 'state', 'date_from', 'date_to'])
        self.env['hr.payslip.line'].flush_model(['total', 'slip_id', 'category_id'])
        self.env['hr.salary.rule.category'].flush_model(['code'])

        self.env.cr.execute("""
            SELECT sum(pl.total)
            FROM hr_payslip as hp, hr_payslip_line as pl, hr_salary_rule_category as rc
            WHERE hp.employee_id = %s
            AND hp.state in ('done', 'paid')
            AND hp.date_from >= %s
            AND hp.date_to <= %s
            AND hp.id = pl.slip_id
            AND rc.id = pl.category_id
            AND rc.code = %s""", (self.employee_id.id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0

    def _sum_worked_days(self, code, from_date, to_date=None):
        self.ensure_one()
        if to_date is None:
            to_date = fields.Date.today()

        query = """
            SELECT sum(hwd.amount)
            FROM hr_payslip hp, hr_payslip_worked_days hwd, hr_work_entry_type hwet
            WHERE hp.state in ('done', 'paid')
            AND hp.id = hwd.payslip_id
            AND hwet.id = hwd.work_entry_type_id
            AND hp.employee_id = %(employee)s
            AND hp.date_to <= %(stop)s
            AND hwet.code = %(code)s
            AND hp.date_from >= %(start)s"""

        self.env.cr.execute(query, {
            'employee': self.employee_id.id,
            'code': code,
            'start': from_date,
            'stop': to_date})
        res = self.env.cr.fetchone()
        return res[0] if res else 0.0

    def _get_base_local_dict(self):
        return {
            'float_round': float_round,
            'float_compare': float_compare,
            "relativedelta": relativedelta,
            "ceil": math.ceil,
            "floor": math.floor,
            'UserError': UserError,
            'date': date,
            'datetime': datetime,
        }

    def _get_localdict(self):
        self.ensure_one()
        # Check for multiple inputs of the same type and keep a copy of
        # them because otherwise they are lost when building the dict
        input_list = [line.code for line in self.input_line_ids if line.code]
        cnt = Counter(input_list)
        multi_input_lines = [k for k, v in cnt.items() if v > 1]
        same_type_input_lines = {line_code: [line for line in self.input_line_ids if line.code == line_code] for line_code in multi_input_lines}

        localdict = {
            **self._get_base_local_dict(),
            **{
                'categories': DefaultDictPayroll(lambda: 0),
                'rules': DefaultDictPayroll(lambda: dict(total=0, amount=0, quantity=0)),
                'payslip': self,
                'worked_days': {line.code: line for line in self.worked_days_line_ids if line.code},
                'inputs': {line.code: line for line in self.input_line_ids if line.code},
                'employee': self.employee_id,
                'contract': self.contract_id,
                'result_rules': DefaultDictPayroll(lambda: dict(total=0, amount=0, quantity=0, rate=0)),
                'same_type_input_lines': same_type_input_lines,
            }
        }
        return localdict

    def _get_rule_name(self, localdict, rule, employee_lang):
        if localdict['result_name']:
            rule_name = localdict['result_name']
        elif rule.code in ['BASIC', 'GROSS', 'NET', 'DEDUCTION',
                           'REIMBURSEMENT']:  # Generated by default_get (no xmlid)
            if rule.code == 'BASIC':  # Note: Crappy way to code this, but _(foo) is forbidden. Make a method in master to be overridden, using the structure code
                if rule.name == "Double Holiday Pay":
                    rule_name = _("Double Holiday Pay")
                if rule.struct_id.name == "CP200: Employees 13th Month":
                    rule_name = _("Prorated end-of-year bonus")
                else:
                    rule_name = _('Basic Salary')
            elif rule.code == "GROSS":
                rule_name = _('Gross')
            elif rule.code == "DEDUCTION":
                rule_name = _('Deduction')
            elif rule.code == "REIMBURSEMENT":
                rule_name = _('Reimbursement')
            elif rule.code == 'NET':
                rule_name = _('Net Salary')
        else:
            rule_name = rule.with_context(lang=employee_lang).name
        return rule_name

    def _get_payslip_line_total(self, amount, quantity, rate, rule):
        self.ensure_one()
        return amount * quantity * rate / 100.0

    def _get_payslip_lines(self):
        line_vals = []
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_("There's no contract set on payslip %s for %s. Check that there is at least a contract set on the employee form.", payslip.name, payslip.employee_id.name))

            localdict = self.env.context.get('force_payslip_localdict', None)
            if localdict is None:
                localdict = payslip._get_localdict()

            rules_dict = localdict['rules']
            result_rules_dict = localdict['result_rules']

            blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            result = {}
            for rule in sorted(payslip.struct_id.rule_ids, key=lambda x: x.sequence):
                if rule.id in blacklisted_rule_ids:
                    continue
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100,
                    'result_name': False
                })
                if rule._satisfy_condition(localdict):
                    # Retrieve the line name in the employee's lang
                    employee_lang = payslip.employee_id.lang or self.env.lang
                    # This actually has an impact, don't remove this line
                    context = {'lang': employee_lang}
                    if rule.code in localdict['same_type_input_lines']:
                        for multi_line_rule in localdict['same_type_input_lines'][rule.code]:
                            localdict['inputs'][rule.code] = multi_line_rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)
                            localdict = rule.category_id._sum_salary_rule_category(localdict,
                                                                                   tot_rule)
                            rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                            line_vals.append({
                                'sequence': rule.sequence,
                                'code': rule.code,
                                'name':  rule_name,
                                'salary_rule_id': rule.id,
                                'contract_id': localdict['contract'].id,
                                'employee_id': localdict['employee'].id,
                                'amount': amount,
                                'quantity': qty,
                                'rate': rate,
                                'total': tot_rule,
                                'slip_id': payslip.id,
                            })
                    else:
                        amount, qty, rate = rule._compute_rule(localdict)
                        #check if there is already a rule computed with that code
                        previous_amount = localdict.get(rule.code, 0.0)
                        #set/overwrite the amount computed for this rule in the localdict
                        tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)
                        localdict[rule.code] = tot_rule
                        result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty, 'rate': rate}
                        rules_dict[rule.code] = rule
                        # sum the amount for its salary category
                        localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
                        rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                        # create/overwrite the rule in the temporary results
                        result[rule.code] = {
                            'sequence': rule.sequence,
                            'code': rule.code,
                            'name': rule_name,
                            'salary_rule_id': rule.id,
                            'contract_id': localdict['contract'].id,
                            'employee_id': localdict['employee'].id,
                            'amount': amount,
                            'quantity': qty,
                            'rate': rate,
                            'total': tot_rule,
                            'slip_id': payslip.id,
                        }
            line_vals += list(result.values())
        return line_vals

    @api.depends('employee_id')
    def _compute_company_id(self):
        for slip in self.filtered(lambda p: p.employee_id):
            slip.company_id = slip.employee_id.company_id

    @api.depends('employee_id', 'contract_domain_ids')
    def _compute_contract_id(self):
        for slip in self:
            if slip.contract_id and slip.employee_id == slip.contract_id.employee_id:
                continue
            slip.contract_id = False
            if not slip.employee_id or not slip.contract_domain_ids:
                continue
            # Add a default contract if not already defined or invalid
            contracts = slip.contract_domain_ids.filtered(lambda c: c.state == 'open')
            if not contracts:
                continue
            slip.contract_id = contracts[0]._origin

    @api.depends('contract_id')
    def _compute_struct_id(self):
        for slip in self.filtered(lambda p: not p.struct_id):
            slip.struct_id = slip.contract_id.structure_type_id.default_struct_id\
                or slip.employee_id.contract_id.structure_type_id.default_struct_id

    def _get_period_name(self, cache):
        self.ensure_one()
        period_name = '%s - %s' % (
            self._format_date_cached(cache, self.date_from),
            self._format_date_cached(cache, self.date_to))
        if self.is_wrong_duration:
            return period_name

        start_date = self.date_from
        end_date = self.date_to
        lang = self.employee_id.lang or self.env.user.lang
        week_start = self.env["res.lang"]._lang_get(lang).week_start
        schedule = self.contract_id.schedule_pay or self.contract_id.structure_type_id.default_schedule_pay
        if schedule == 'monthly':
            period_name = self._format_date_cached(cache, start_date, "MMMM Y")
        elif schedule == 'quarterly':
            current_year_quarter = math.ceil(start_date.month / 3)
            period_name = _("Quarter %s of %s", current_year_quarter, start_date.year)
        elif schedule == 'semi-annually':
            year_half = start_date.replace(day=1, month=6)
            is_first_half = start_date < year_half
            period_name = _("1st semester of %s", start_date.year)\
                if is_first_half\
                else _("2nd semester of %s", start_date.year)
        elif schedule == 'annually':
            period_name = start_date.year
        elif schedule == 'weekly':
            wk_num = start_date.strftime('%U') if week_start == '7' else start_date.strftime('%W')
            period_name = _('Week %(week_number)s of %(year)s', week_number=wk_num, year=start_date.year)
        elif schedule == 'bi-weekly':
            week = int(start_date.strftime("%U") if week_start == '7' else start_date.strftime("%W"))
            first_week = week - 1 + week % 2
            period_name = _("Weeks %(week)s and %(week1)s of %(year)s",
                week=first_week, week1=first_week + 1, year=start_date.year)
        elif schedule == 'bi-monthly':
            start_date_string = self._format_date_cached(cache, start_date, "MMMM Y")
            end_date_string = self._format_date_cached(cache, end_date, "MMMM Y")
            period_name = _("%s and %s", start_date_string, end_date_string)
        return period_name

    def _format_date_cached(self, cache, date, date_format=False):
        key = (date, date_format)
        if key not in cache:
            lang = self.employee_id.lang or self.env.user.lang
            cache[key] = format_date(env=self.env, value=date, lang_code=lang, date_format=date_format)
        return cache[key]

    @api.depends('employee_id', 'struct_id', 'date_from', 'date_to')
    def _compute_name(self):
        formated_date_cache = {}
        for slip in self.filtered(lambda p: p.employee_id and p.date_from and p.date_to):
            lang = slip.employee_id.lang or self.env.user.lang
            context = {'lang': lang}
            payslip_name = slip.struct_id.payslip_name or _('Salary Slip')
            del context

            slip.name = '%(payslip_name)s - %(employee_name)s - %(dates)s' % {
                'payslip_name': payslip_name,
                'employee_name': slip.employee_id.name,
                'dates': slip._get_period_name(formated_date_cache),
            }

    @api.depends('date_from', 'date_to', 'struct_id')
    def _compute_warning_message(self):
        for slip in self.filtered(lambda p: p.date_to):
            slip.warning_message = False
            warnings = []
            if slip.contract_id and (slip.date_from < slip.contract_id.date_start
                    or (slip.contract_id.date_end and slip.date_to > slip.contract_id.date_end)):
                warnings.append(_("The period selected does not match the contract validity period."))

            if slip.date_to > date_utils.end_of(fields.Date.today(), 'month'):
                warnings.append(_(
                    "Work entries may not be generated for the period from %(start)s to %(end)s.",
                    start=date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1),
                    end=slip.date_to,
                ))

            if (slip.contract_id.schedule_pay or slip.contract_id.structure_type_id.default_schedule_pay)\
                    and slip.date_from + slip._get_schedule_timedelta() != slip.date_to:
                warnings.append(_("The duration of the payslip is not accurate according to the structure type."))

            if warnings:
                warnings = [_("This payslip can be erroneous :")] + warnings
                slip.warning_message = "\n  ・ ".join(warnings)

    @api.depends('date_from', 'date_to', 'struct_id')
    def _compute_is_wrong_duration(self):
        for slip in self:
            slip.is_wrong_duration = slip.date_to and (
                slip.contract_id.schedule_pay
                or slip.contract_id.structure_type_id.default_schedule_pay
            ) and (
                slip.date_from + slip._get_schedule_timedelta() != slip.date_to
            )

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_worked_days_line_ids(self):
        if not self or self.env.context.get('salary_simulation'):
            return
        valid_slips = self.filtered(lambda p: p.employee_id and p.date_from and p.date_to and p.contract_id and p.struct_id)
        if not valid_slips:
            return
        # Make sure to reset invalid payslip's worked days line
        self.update({'worked_days_line_ids': [(5, 0, 0)]})
        # Ensure work entries are generated for all contracts
        generate_from = min(p.date_from for p in valid_slips) + relativedelta(days=-1)
        generate_to = max(p.date_to for p in valid_slips) + relativedelta(days=1)
        self.contract_id.generate_work_entries(generate_from, generate_to)

        work_entries = self.env['hr.work.entry'].search([
            ('date_stop', '<=', generate_to),
            ('date_start', '>=', generate_from),
            ('contract_id', 'in', self.contract_id.ids),
        ])
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id.id] += work_entry

        for slip in valid_slips:
            if not slip.struct_id.use_worked_day_lines:
                continue

            # convert slip.date_to to a datetime with max time to compare correctly in filtered_domain.
            slip_tz = pytz.timezone(slip.contract_id.resource_calendar_id.tz)
            utc = pytz.timezone('UTC')
            date_from = slip_tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(utc).replace(tzinfo=None)
            date_to = slip_tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(utc).replace(tzinfo=None)
            payslip_work_entries = work_entries_by_contract[slip.contract_id].filtered_domain([
                ('date_stop', '<=', date_to),
                ('date_start', '>=', date_from),
            ])
            payslip_work_entries._check_undefined_slots(slip.date_from, slip.date_to)
            # YTI Note: We can't use a batched create here as the payslip may not exist
            slip.update({'worked_days_line_ids': slip._get_new_worked_days_lines()})

    def _get_credit_time_lines(self):
        lines_vals = self._get_worked_day_lines(domain=[('is_credit_time', '=', True)], check_out_of_contract=False)
        for line_vals in lines_vals:
            line_vals['is_credit_time'] = True
        return lines_vals

    def _get_new_worked_days_lines(self):
        if self.struct_id.use_worked_day_lines:
            if not self.contract_id.time_credit:
                return [(0, 0, vals) for vals in self._get_worked_day_lines()]
            worked_days_line_values = self._get_worked_day_lines(domain=[('is_credit_time', '=', False)])
            for vals in worked_days_line_values:
                vals['is_credit_time'] = False
            credit_time_line_values = self._get_credit_time_lines()
            return [(0, 0, vals) for vals in worked_days_line_values + credit_time_line_values]
        return []

    def _get_salary_line_total(self, code):
        _logger.warning('The method _get_salary_line_total is deprecated in favor of _get_line_values')
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum([line.total for line in lines])

    def _get_salary_line_quantity(self, code):
        _logger.warning('The method _get_salary_line_quantity is deprecated in favor of _get_line_values')
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum([line.quantity for line in lines])

    def _get_line_values(self, code_list, vals_list=None, compute_sum=False):
        if vals_list is None:
            vals_list = ['total']
        valid_values = {'quantity', 'amount', 'total'}
        if set(vals_list) - valid_values:
            raise UserError(_('The following values are not valid:\n%s', '\n'.join(list(set(vals_list) - valid_values))))
        result = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(vals_list, 0.0)))
        if not self or not code_list:
            return result
        self.env.flush_all()
        selected_fields = ','.join('SUM(%s) AS %s' % (vals, vals) for vals in vals_list)
        self.env.cr.execute("""
            SELECT
                p.id,
                pl.code,
                %s
            FROM hr_payslip_line pl
            JOIN hr_payslip p
            ON p.id IN %s
            AND pl.slip_id = p.id
            AND pl.code IN %s
            GROUP BY p.id, pl.code
        """ % (selected_fields, '%s', '%s'), (tuple(self.ids), tuple(code_list)))
        # self = hr.payslip(1, 2)
        # request_rows = [
        #     {'id': 1, 'code': 'IP', 'total': 100, 'quantity': 1},
        #     {'id': 1, 'code': 'IP.DED', 'total': 200, 'quantity': 1},
        #     {'id': 2, 'code': 'IP', 'total': -2, 'quantity': 1},
        #     {'id': 2, 'code': 'IP.DED', 'total': -3, 'quantity': 1}
        # ]
        request_rows = self.env.cr.dictfetchall()
        # result = {
        #     'IP': {
        #         'sum': {'quantity': 2, 'total': 300},
        #         1: {'quantity': 1, 'total': 100},
        #         2: {'quantity': 1, 'total': 200},
        #     },
        #     'IP.DED': {
        #         'sum': {'quantity': 2, 'total': -5},
        #         1: {'quantity': 1, 'total': -2},
        #         2: {'quantity': 1, 'total': -3},
        #     },
        # }
        for row in request_rows:
            code = row['code']
            payslip_id = row['id']
            for vals in vals_list:
                if compute_sum:
                    result[code]['sum'][vals] += row[vals] or 0.0
                result[code][payslip_id][vals] += row[vals] or 0.0
        return result

    def _get_worked_days_line_values(self, code_list, vals_list=None, compute_sum=False):
        if vals_list is None:
            vals_list = ['amount']
        valid_values = {'number_of_hours', 'number_of_days', 'amount'}
        if set(vals_list) - valid_values:
            raise UserError(_('The following values are not valid:\n%s', '\n'.join(list(set(vals_list) - valid_values))))
        result = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(vals_list, 0.0)))
        if not self or not code_list:
            return result
        self.env.flush_all()
        selected_fields = ','.join('SUM(%s) AS %s' % (vals, vals) for vals in vals_list)
        self.env.cr.execute("""
            SELECT
                p.id,
                wet.code,
                %s
            FROM hr_payslip_worked_days wd
            JOIN hr_work_entry_type wet ON wet.id = wd.work_entry_type_id
            JOIN hr_payslip p ON p.id IN %s
            AND wd.payslip_id = p.id
            AND wet.code IN %s
            GROUP BY p.id, wet.code
        """ % (selected_fields, '%s', '%s'), (tuple(self.ids), tuple(code_list)))
        # self = hr.payslip(1, 2)
        # request_rows = [
        #     {'id': 1, 'code': 'WORK100', 'amount': 100, 'number_of_days': 1},
        #     {'id': 1, 'code': 'LEAVE100', 'amount': 200, 'number_of_days': 1},
        #     {'id': 2, 'code': 'WORK100', 'amount': -2, 'number_of_days': 1},
        #     {'id': 2, 'code': 'LEAVE100', 'amount': -3, 'number_of_days': 1}
        # ]
        request_rows = self.env.cr.dictfetchall()
        # result = {
        #     'IP': {
        #         'sum': {'number_of_days': 2, 'amount': 300},
        #         1: {'number_of_days': 1, 'amount': 100},
        #         2: {'number_of_days': 1, 'amount': 200},
        #     },
        #     'LEAVE100': {
        #         'sum': {'number_of_days': 2, 'amount': -5},
        #         1: {'number_of_days': 1, 'amount': -2},
        #         2: {'number_of_days': 1, 'amount': -3},
        #     },
        # }
        for row in request_rows:
            code = row['code']
            payslip_id = row['id']
            for vals in vals_list:
                if compute_sum:
                    result[code]['sum'][vals] += row[vals] or 0.0
                result[code][payslip_id][vals] += row[vals] or 0.0
        return result

    def _get_worked_days_line_amount(self, code):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code == code)
        return sum([wd.amount for wd in wds])

    def _get_worked_days_line_number_of_hours(self, code):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code == code)
        return sum([wd.number_of_hours for wd in wds])

    def _get_worked_days_line_number_of_days(self, code):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code == code)
        return sum([wd.number_of_days for wd in wds])

    def _get_input_line_amount(self, code):
        lines = self.input_line_ids.filtered(lambda line: line.code == code)
        return sum([line.amount for line in lines])

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if options and options.get('toolbar'):
            for view_type in res['views']:
                res['views'][view_type]['toolbar'].pop('print', None)
        return res

    def action_print_payslip(self):
        return {
            'name': 'Payslip',
            'type': 'ir.actions.act_url',
            'url': '/print/payslips?list_ids=%(list_ids)s' % {'list_ids': ','.join(str(x) for x in self.ids)},
        }

    def action_export_payslip(self):
        self.ensure_one()
        return {
            "name": "Debug Payslip",
            "type": "ir.actions.act_url",
            "url": "/debug/payslip/%s" % self.id,
        }

    def _get_contract_wage(self):
        self.ensure_one()
        return self.contract_id._get_contract_wage()

    def _get_paid_amount(self):
        self.ensure_one()
        if self.env.context.get('no_paid_amount'):
            return 0.0
        if not self.worked_days_line_ids:
            return self._get_contract_wage()
        total_amount = 0
        for line in self.worked_days_line_ids:
            total_amount += line.amount
        return total_amount

    def _get_unpaid_amount(self):
        self.ensure_one()
        return self._get_contract_wage() - self._get_paid_amount()

    def _is_outside_contract_dates(self):
        self.ensure_one()
        payslip = self
        contract = self.contract_id
        return contract.date_start > payslip.date_to or (contract.date_end and contract.date_end < payslip.date_from)

    def _get_data_files_to_update(self):
        # Note: Use lists as modules/files order should be maintained
        return []

    def _update_payroll_data(self):
        data_to_update = self._get_data_files_to_update()
        _logger.info("Update payroll static data")
        idref = {}
        for module_name, files_to_update in data_to_update:
            for file_to_update in files_to_update:
                convert_file(self.env, module_name, file_to_update, idref)

    def action_edit_payslip_lines(self):
        self.ensure_one()
        if not self.user_has_groups('hr_payroll.group_hr_payroll_manager'):
            raise UserError(_('This action is restricted to payroll managers only.'))
        if self.state == 'done':
            raise UserError(_('This action is forbidden on validated payslips.'))
        wizard = self.env['hr.payroll.edit.payslip.lines.wizard'].create({
            'payslip_id': self.id,
            'line_ids': [(0, 0, {
                'sequence': line.sequence,
                'code': line.code,
                'name': line.name,
                'salary_rule_id': line.salary_rule_id.id,
                'contract_id': line.contract_id.id,
                'employee_id': line.employee_id.id,
                'amount': line.amount,
                'quantity': line.quantity,
                'rate': line.rate,
                'slip_id': self.id}) for line in self.line_ids],
            'worked_days_line_ids': [(0, 0, {
                'name': line.name,
                'sequence': line.sequence,
                'code': line.code,
                'work_entry_type_id': line.work_entry_type_id.id,
                'number_of_days': line.number_of_days,
                'number_of_hours': line.number_of_hours,
                'amount': line.amount,
                'slip_id': self.id}) for line in self.worked_days_line_ids]
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Payslip Lines'),
            'res_model': 'hr.payroll.edit.payslip.lines.wizard',
            'view_mode': 'form',
            'target': 'new',
            'binding_model_id': self.env['ir.model.data']._xmlid_to_res_id('hr_payroll.model_hr_payslip'),
            'binding_view_types': 'form',
            'res_id': wizard.id
        }

    @api.model
    def _cron_generate_pdf(self, batch_size=False):
        payslips = self.search([
            ('state', 'in', ['done', 'paid']),
            ('queued_for_pdf', '=', True),
        ])
        if payslips:
            BATCH_SIZE = batch_size or 50
            payslips_batch = payslips[:BATCH_SIZE]
            payslips_batch._generate_pdf()
            payslips_batch.write({'queued_for_pdf': False})
            # if necessary, retrigger the cron to generate more pdfs
            if len(payslips) > BATCH_SIZE:
                self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
                return True

        lines = self.env['hr.payroll.employee.declaration'].search([('pdf_to_generate', '=', True)])
        if lines:
            BATCH_SIZE = batch_size or 30
            lines_batch = lines[:BATCH_SIZE]
            lines_batch._generate_pdf()
            lines_batch.write({'pdf_to_generate': False})
            # if necessary, retrigger the cron to generate more pdfs
            if len(lines) > BATCH_SIZE:
                self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
                return True
        return False

    # Payroll Dashboard
    @api.model
    def _dashboard_default_action(self, name, res_model, res_ids, additional_context=None):
        if additional_context is None:
            additional_context = {}
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': res_model,
            'context': {**self.env.context, **additional_context},
            'domain': [('id', 'in', res_ids)],
            'views': [[False, 'list'], [False, 'kanban'], [False, 'form']],
            'view_mode': 'tree,kanban,form',
        }

    @api.model
    def _get_dashboard_warnings(self):
        # Retrieve the different warnings to display on the actions section (box on the left)
        result = []

        # Employees section
        employees_default_title = _('Employees')
        # Retrieve employees:
        # - with no open contract, and date_end in the past
        # - with no contract, and not green draft contract
        employees_without_contracts = self.env['hr.employee']
        all_employees = self.env['hr.employee'].search([
            ('employee_type', '=', 'employee'),
            ('company_id', 'in', self.env.companies.ids),
        ])
        today = fields.Date.today()
        for employee in all_employees:
            contract = employee.contract_id.sudo()
            if contract and contract.date_end and contract.date_end < today:
                employees_without_contracts += employee
            elif not contract:
                existing_draft_contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                    ('company_id', '=', employee.company_id.id),
                    ('state', '=', 'draft'),
                    ('kanban_state', '=', 'done'),
                ])
                if not existing_draft_contract:
                    employees_without_contracts += employee
        if employees_without_contracts:
            result.append({
                'string': _('Employees Without Running Contracts'),
                'count': len(employees_without_contracts),
                'action': self._dashboard_default_action(employees_default_title, 'hr.employee', employees_without_contracts.ids),
            })

        # Retrieve employees whose company on contract is different than employee's company
        employee_with_different_company_on_contract = self.env['hr.employee']
        contracts = self.sudo().env['hr.contract'].search([
            ('state', 'in', ['draft', 'open']),
            ('employee_id', 'in', all_employees.ids),
        ])

        for contract in contracts:
            if contract.employee_id.company_id != contract.company_id:
                employee_with_different_company_on_contract |= contract.employee_id
        if employee_with_different_company_on_contract:
            result.append({
                'string': _('Employee whose contracts and company are differents'),
                'count': len(employee_with_different_company_on_contract),
                'action': self._dashboard_default_action(employees_default_title, 'hr.employee', employee_with_different_company_on_contract.ids),
            })

        # Retrieves last batches (this month, or last month)
        batch_limit_date = fields.Date.today() - relativedelta(months=1, day=1)
        batch_group_read = self.env['hr.payslip.run'].with_context(lang='en_US')._read_group(
            [('date_start', '>=', fields.Date.today() - relativedelta(months=1, day=1))],
            groupby=['date_start:month'],
            order='date_start:month desc')
        # Keep only the last month
        batch_group_read = batch_group_read[:1]
        if batch_group_read:
            min_date = batch_group_read[-1][0] or batch_limit_date
            last_batches = self.env['hr.payslip.run'].search([('date_start', '>=', min_date)])
        else:
            last_batches = self.env['hr.payslip.run']

        payslips_with_negative_net = self.env['hr.payslip']

        employee_payslips = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
        employee_calendar_contracts = defaultdict(lambda: defaultdict(lambda: self.env['hr.contract']))
        employee_payslip_contracts = defaultdict(lambda: self.env['hr.contract'])
        for slip in last_batches.slip_ids:
            if slip.state == 'cancel':
                continue
            employee = slip.employee_id
            contract = slip.contract_id
            calendar = contract.resource_calendar_id
            struct = slip.struct_id

            employee_payslips[struct][employee] |= slip

            employee_calendar_contracts[employee][calendar] |= contract

            employee_payslip_contracts[employee] |= contract

            if slip.net_wage < 0:
                payslips_with_negative_net |= slip

        employees_previous_contract = self.env['hr.employee']
        for employee, used_contracts in employee_payslip_contracts.items():
            if employee.contract_id not in used_contracts:
                employees_previous_contract |= employee

        employees_multiple_payslips = self.env['hr.payslip']
        for dummy, employee_slips in employee_payslips.items():
            for employee, payslips in employee_slips.items():
                if len(payslips) > 1:
                    employees_multiple_payslips |= payslips
        if employees_multiple_payslips:
            multiple_payslips_str = _('Employees With Multiple Open Payslips of Same Type')
            result.append({
                'string': multiple_payslips_str,
                'count': len(employees_multiple_payslips.employee_id),
                'action': self._dashboard_default_action(multiple_payslips_str, 'hr.payslip', employees_multiple_payslips.ids, additional_context={'search_default_group_by_employee_id': 1}),
            })

        employees_missing_payslip = self.env['hr.employee'].search([
            ('company_id', 'in', last_batches.company_id.ids),
            ('id', 'not in', last_batches.slip_ids.employee_id.ids),
            ('contract_warning', '=', False)])
        if employees_missing_payslip:
            missing_payslips_str = _('Employees (With Running Contracts) missing from open batches')
            result.append({
                'string': missing_payslips_str,
                'count': len(employees_missing_payslip),
                'action': self._dashboard_default_action(missing_payslips_str, 'hr.contract', employees_missing_payslip.contract_id.ids),
            })

        # Retrieve employees with both draft and running contracts
        ambiguous_domain = [
            ('company_id', 'in', self.env.companies.ids),
            ('employee_id', '!=', False),
            '|',
                '&',
                    ('state', '=', 'draft'),
                    ('kanban_state', '!=', 'done'),
                ('state', '=', 'open')]
        employee_contract_groups = self.env['hr.contract']._read_group(
            ambiguous_domain,
            groupby=['employee_id'], having=[('state:count_distinct', '=', 2)])
        ambiguous_employee_ids = [employee.id for [employee] in employee_contract_groups]
        if ambiguous_employee_ids:
            ambiguous_contracts_str = _('Employees With Both New And Running Contracts')
            ambiguous_contracts = self.env['hr.contract'].search(
                AND([ambiguous_domain, [('employee_id', 'in', ambiguous_employee_ids)]]))
            result.append({
                'string': ambiguous_contracts_str,
                'count': len(ambiguous_employee_ids),
                'action': self._dashboard_default_action(ambiguous_contracts_str, 'hr.contract', ambiguous_contracts.ids, additional_context={'search_default_group_by_employee': 1}),
            })

        # Work Entries section
        start_month = fields.Date.today().replace(day=1)
        next_month = start_month + relativedelta(months=1)
        work_entries_in_conflict = self.env['hr.work.entry'].search_count([
            ('state', '=', 'conflict'),
            ('date_stop', '>=', start_month),
            ('date_start', '<', next_month)])
        if work_entries_in_conflict:
            result.append({
                'string': _('Conflicts'),
                'count': work_entries_in_conflict,
                'action': 'hr_work_entry.hr_work_entry_action_conflict',
            })

        multiple_schedule_contracts = self.env['hr.contract']
        for employee, calendar_contracts in employee_calendar_contracts.items():
            if len(calendar_contracts) > 1:
                for dummy, contracts in calendar_contracts.items():
                    multiple_schedule_contracts |= contracts
        if multiple_schedule_contracts:
            schedule_change_str = _('Working Schedule Changes')
            result.append({
                'string': schedule_change_str,
                'count': len(multiple_schedule_contracts.employee_id),
                'action': self._dashboard_default_action(schedule_change_str, 'hr.contract', multiple_schedule_contracts.ids, additional_context={'search_default_group_by_employee': 1}),
            })

        # Nearly expired contracts
        date_today = fields.Date.today()
        HRContract = self.env['hr.contract']
        nearly_expired_contracts = self.env['hr.contract']
        for company in self.env.companies:
            outdated_days = date_today + relativedelta(days=company.contract_expiration_notice_period)
            nearly_expired_contracts += HRContract._get_nearly_expired_contracts(outdated_days, company.id)
        if nearly_expired_contracts:
            result.append({
                'string': _('Running contracts coming to an end'),
                'count': len(nearly_expired_contracts),
                'action': self._dashboard_default_action('Employees with running contracts coming to an end', 'hr.contract', nearly_expired_contracts.ids)
            })

        # Payslip Section
        if employees_previous_contract:
            result.append({
                'string': _('Payslips Generated On Previous Contract'),
                'count': len(employees_previous_contract),
                'action': self._dashboard_default_action(_('Employees with payslips generated on the previous contract'), 'hr.employee', employees_previous_contract.ids),
            })
        if payslips_with_negative_net:
            result.append({
                'string': _('Payslips With Negative Amounts'),
                'count': len(payslips_with_negative_net),
                'action': self._dashboard_default_action(_('Payslips with negative NET'), 'hr.payslip', payslips_with_negative_net.ids),
            })

        # new contracts warning
        new_contracts = self.env['hr.contract'].search([
            ('state', '=', 'draft'),
            ('employee_id', '!=', False),
            ('kanban_state', '=', 'normal')])
        if new_contracts:
            new_contracts_str = _('New Contracts')
            result.append({
                'string': new_contracts_str,
                'count': len(new_contracts),
                'action': self._dashboard_default_action(new_contracts_str, 'hr.contract', new_contracts.ids)
            })

        # Employees Without ID Number
        employees_wo_id = self.env['hr.employee'].search([
            ('identification_id', '=', False),
        ])
        if employees_wo_id:
            no_id_str = _('Employees Without Identification Number')
            result.append({
                'string': no_id_str,
                'count': len(employees_wo_id),
                'action': self._dashboard_default_action(no_id_str, 'hr.employee', employees_wo_id.ids)
            })

        # Employees Without Bank Account Number
        employees_wo_bnk_acc = self.env['hr.employee'].search([
            ('bank_account_id', '=', False),
            ('contract_id', '!=', False),
        ])
        if employees_wo_bnk_acc:
            no_bnk_acc_id_str = _('Employees Without Bank account Number')
            result.append({
                'string': no_bnk_acc_id_str,
                'count': len(employees_wo_bnk_acc),
                'action': self._dashboard_default_action(no_bnk_acc_id_str, 'hr.employee', employees_wo_bnk_acc.ids)
            })

        return result

    def _get_employee_stats_actions(self):
        result = []
        today = fields.Date.today()
        HRContract = self.env['hr.contract']
        new_contracts = HRContract.search([
            ('state', '=', 'open'),
            ('kanban_state', '=', 'normal'),
            ('date_start', '>=', today + relativedelta(months=-3, day=1))])

        past_contracts_grouped_by_employee_id = {
            employee.id
            for [employee] in HRContract._read_group([
                ('employee_id', 'in', new_contracts.employee_id.ids),
                ('date_end', '<', today),
                ('state', 'in', ['open', 'close']),
                ('id', 'not in', new_contracts.ids)
            ], groupby=['employee_id'])
        }

        new_contracts_without_past_contract = HRContract
        for new_contract in new_contracts:
            if new_contract.employee_id.id not in past_contracts_grouped_by_employee_id:
                new_contracts_without_past_contract |= new_contract

        if new_contracts_without_past_contract:
            new_contracts_str = _('New Employees')
            employees_from_new_contracts = new_contracts_without_past_contract.mapped('employee_id')
            new_employees = {
                'string': new_contracts_str,
                'count': len(employees_from_new_contracts),
                'action': self._dashboard_default_action(new_contracts_str, 'hr.employee', employees_from_new_contracts.ids),
            }
            new_employees['action']['views'][0] = [self.env.ref('hr_payroll.payroll_hr_employee_view_tree_employee_trends').id, 'list']
            result.append(new_employees)

        gone_employees = self.env['hr.employee'].with_context(active_test=False).search([
            ('departure_date', '>=', today + relativedelta(months=-1, day=1)),
            ('company_id', 'in', self.env.companies.ids),
        ])
        if gone_employees:
            gone_employees_str = _('Last Departures')
            result.append({
                'string': gone_employees_str,
                'count': len(gone_employees),
                'action': self.with_context(active_test=False)._dashboard_default_action(
                    gone_employees_str, 'hr.employee', gone_employees.ids),
            })
        return result

    @api.model
    def _get_dashboard_stat_employer_cost_codes(self):
        costs = self.env['hr.salary.rule'].search_read([
            ('appears_on_employee_cost_dashboard', '=', True)],
            fields=['code', 'name'])
        cost_codes = {}

        for cost in costs:
            cost_codes[cost['code']] = cost['name']
        return cost_codes

    @api.model
    def _get_dashboard_stats_employer_cost(self):
        today = fields.Date.context_today(self)
        date_formats = {
            'monthly': 'MMMM y',
            'yearly': 'y',
        }
        employer_cost = {
            'type': 'stacked_bar',
            'title': _('Employer Cost'),
            'label': _('Employer Cost'),
            'id': 'employer_cost',
            'is_sample': False,
            'actions': [],
            'data': {
                'monthly': defaultdict(lambda: [{}, {}, {}]),
                'yearly': defaultdict(lambda: [{}, {}, {}]),
            },
        }
        # Retrieve employer costs over the last 3 months
        last_payslips = self.env['hr.payslip'].search([
            ('state', '!=', 'cancel'),
            ('date_from', '>=', fields.Date.today() + relativedelta(months=-2, day=1)),
            ('date_to', '<=', fields.Date.today() + relativedelta(day=31))
        ])
        if not last_payslips:
            employer_cost['is_sample'] = True
        cost_codes = self._get_dashboard_stat_employer_cost_codes()
        line_values = last_payslips._get_line_values(cost_codes.keys())
        for slip in last_payslips:
            for code, code_desc in cost_codes.items():
                start = slip.date_from
                end = today
                idx = -((end.year - start.year) * 12 + (end.month - start.month) - 2)
                amount = employer_cost['data']['monthly'][code_desc][idx].get('value', 0.0)
                amount += line_values[code][slip.id]['total']
                employer_cost['data']['monthly'][code_desc][idx]['value'] = amount
                if not employer_cost['data']['monthly'][code_desc][idx].get('label'):
                    period_str = format_date(self.env, start, date_format=date_formats['monthly'])
                    employer_cost['data']['monthly'][code_desc][idx]['label'] = period_str
        # Retrieve employer costs over the last 3 years
        last_payslips = self.env['hr.payslip'].search([
            ('state', '!=', 'cancel'),
            ('date_from', '>=', fields.Date.today() + relativedelta(years=-2, day=1)),
            ('date_to', '<=', fields.Date.today() + relativedelta(month=12, day=31))
        ])
        line_values = last_payslips._get_line_values(cost_codes.keys())
        for slip in last_payslips:
            for code, code_desc in cost_codes.items():
                start = slip.date_from
                end = today
                idx = -(end.year - start.year - 2)
                amount = employer_cost['data']['yearly'][code_desc][idx].get('value', 0.0)
                amount += line_values[code][slip.id]['total']
                employer_cost['data']['yearly'][code_desc][idx]['value'] = amount
                if not employer_cost['data']['yearly'][code_desc][idx].get('label'):
                    period_str = format_date(self.env, start, date_format=date_formats['yearly'])
                    employer_cost['data']['yearly'][code_desc][idx]['label'] = period_str
        # Nullify empty sections
        for i in range(3):
            for code, code_desc in cost_codes.items():
                if not employer_cost['data']['monthly'][code_desc][i]:
                    value = 0 if not employer_cost['is_sample'] else random.randint(1000, 1500)
                    employer_cost['data']['monthly'][code_desc][i]['value'] = value
                    if not employer_cost['data']['monthly'][code_desc][i].get('label'):
                        label = format_date(self.env, today + relativedelta(months=i-2), date_format=date_formats['monthly'])
                        employer_cost['data']['monthly'][code_desc][i]['label'] = label
                if not employer_cost['data']['yearly'][code_desc][i]:
                    value = 0 if not employer_cost['is_sample'] else random.randint(10000, 15000)
                    employer_cost['data']['yearly'][code_desc][i]['value'] = value
                    if not employer_cost['data']['yearly'][code_desc][i].get('label'):
                        label = format_date(self.env, today + relativedelta(years=i-2), date_format=date_formats['yearly'])
                        employer_cost['data']['yearly'][code_desc][i]['label'] = label
        # Format/Round at the end as the method cost is heavy
        for dummy, data_by_code in employer_cost['data'].items():
            for code, data_by_type in data_by_code.items():
                for data_dict in data_by_type:
                    value = round(data_dict['value'], 2)
                    data_dict['value'] = value
                    data_dict['formatted_value'] = format_amount(self.env, value, self.env.company.currency_id)
        return employer_cost

    @api.model
    def _get_dashboard_stat_employee_trends(self):
        today = fields.Date.context_today(self)
        employees_trends = {
            'type': 'bar',
            'title': _('Employee Trends'),
            'label': _('Employee Count'),
            'id': 'employees',
            'is_sample': False,
            'actions': self._get_employee_stats_actions(),
            'data': {
                'monthly': [{}, {}, {}],
                'yearly': [{}, {}, {}],
            },
        }
        # These are all the periods for which we need data
        periods = [
            # Last month
            (today - relativedelta(months=1, day=1), today - relativedelta(day=1, days=1), 'monthly,past'),
            # This month
            (today - relativedelta(day=1), today + relativedelta(months=1, day=1, days=-1), 'monthly,present'),
            # Next month
            (today + relativedelta(months=1, day=1), today + relativedelta(months=2, day=1, days=-1), 'monthly,future'),
            # Last year
            (today - relativedelta(years=1, month=1, day=1), today - relativedelta(years=1, month=12, day=31), 'yearly,past'),
            # This year
            (today - relativedelta(month=1, day=1), today + relativedelta(month=12, day=31), 'yearly,present'),
            # Next year
            (today + relativedelta(years=1, month=1, day=1), today + relativedelta(years=1, month=12, day=31), 'yearly,future'),
        ]
        periods_str = ', '.join(
            "(DATE '%(date_from)s', DATE '%(date_to)s', '%(date_type)s')" % {
                'date_from': p[0].strftime('%Y-%m-%d'),
                'date_to': p[1].strftime('%Y-%m-%d'),
                'date_type': p[2],
            } for p in periods)
        # Fetch our statistics
        # Contracts are joined by our period using the usual state/date conditions
        # and aggregates are used to collect data directly from our database
        # avoiding unnecessary orm overhead
        self.env.cr.execute("""
        WITH periods AS (
            SELECT *
              FROM (VALUES %s
              ) x(start, _end, _type)
        )
        -- fetch all contracts matching periods from `periods`
        SELECT p.start, p._end, p._type, ARRAY_AGG(c.id),
               COUNT (DISTINCT c.employee_id) as employee_count
          FROM periods p
          JOIN hr_contract c
            ON (c.date_end >= p.start OR c.date_end IS NULL)
           AND c.date_start <= p._end
           AND (c.state IN ('open', 'close')
            OR (c.state = 'done' AND c.kanban_state='normal'))
           AND c.employee_id IS NOT NULL
           AND c.active = TRUE
           AND c.company_id IN %%s
      GROUP BY p.start, p._end, p._type
        """ % (periods_str), (tuple(self.env.companies.ids),))
        period_indexes = {
            'past': 0,
            'present': 1,
            'future': 2,
        }
        date_formats = {
            'monthly': 'MMMM y',
            'yearly': 'y',
        }
        # Collect data in our result
        for res in self.env.cr.dictfetchall():
            period_type, _type = res['_type'].split(',')  # Ex: yearly,past
            start = res['start']
            period_idx = period_indexes[_type]
            period_str = format_date(self.env, start, date_format=date_formats[period_type])
            # The data is formatted for the chart module
            employees_trends['data'][period_type][period_idx] = {
                'label': period_str,
                'value': res['employee_count'],
                'name': period_str,
            }

        # Generates a point as sample data
        def make_sample_data(period_str, period_type, chart_type):
            if chart_type == 'line':
                return {'x': period_str, 'name': period_str, 'y': random.randint(1000, 1500)}
            return {'value': random.randint(1000, 1500), 'label': period_str, 'type': period_type}

        # Generates empty data in case a column is missing
        def make_null_data(period_str, period_type, chart_type):
            if chart_type == 'line':
                return {'x': period_str, 'name': period_str, 'y': 0}
            return {'value': 0, 'label': period_str, 'type': period_type}

        make_data = make_null_data
        period_types = ['monthly', 'yearly']

        if all(not data for data in employees_trends['data']['monthly']):
            employees_trends['is_sample'] = True
            make_data = make_sample_data

        # Go through all the data and create null or sample values where necessary
        for start, dummy, p_types in periods:
            _type, _time = p_types.split(',')
            i = period_indexes[_time]
            for period in period_types:
                period_str = format_date(self.env, start, date_format=date_formats[period])
                if not employees_trends['data'][_type][i]:
                    employees_trends['data'][_type][i] = make_data(
                        period_str, _type, employees_trends['type'])
        return employees_trends

    @api.model
    def _get_dashboard_stats(self):
        # Retrieve the different stats to display on the stats sections
        # This function fills in employees and employer costs statistics
        # Default data, replaced by sample data if empty after query
        employees_trends = self._get_dashboard_stat_employee_trends()
        employer_cost = self._get_dashboard_stats_employer_cost()

        return [employer_cost, employees_trends]

    @api.model
    def _get_dashboard_default_sections(self):
        return ['batches', 'stats']

    @api.model
    def _get_dashboard_batch_fields(self):
        return ['id', 'date_start', 'name', 'state', 'payslip_count']

    @api.model
    def get_payroll_dashboard_data(self, sections=None):
        # Entry point for getting the dashboard data
        # `sections` defines which part of the data we want to include/exclude
        if sections is None:
            sections = self._get_dashboard_default_sections()
        result = {}
        if 'batches' in sections:
            # Batches are loaded for the last 3 months with batches, for example if there are no batches for
            # the summer and september is loaded, we want to get september, june, may.
            # Limit to max - 1 year
            batch_limit_date = fields.Date.today() - relativedelta(years=1, day=1)
            batch_group_read = self.env['hr.payslip.run'].with_context(lang='en_US')._read_group(
                [('date_start', '>=', batch_limit_date)],
                groupby=['date_start:month'],
                limit=20,
                order='date_start:month desc')
            # Keep only the last 3 months
            batch_group_read = batch_group_read[:3]
            if batch_group_read:
                min_date = batch_group_read[-1][0] or fields.Date.today() - relativedelta(months=1, day=1)
                batches_read_result = self.env['hr.payslip.run'].search_read(
                    [('date_start', '>=', min_date)],
                    fields=self._get_dashboard_batch_fields())
            else:
                batches_read_result = []
            translated_states = dict(self.env['hr.payslip.run']._fields['state']._description_selection(self.env))
            for batch_read in batches_read_result:
                batch_read.update({
                    'name': f"{batch_read['name']} ({format_date(self.env, batch_read['date_start'], date_format='MM/y')})",
                    'payslip_count': _('(%s Payslips)', batch_read['payslip_count']),
                    'state': translated_states.get(batch_read['state'], _('Unknown State')),
                })
            result['batches'] = batches_read_result
        if 'stats' in sections:
            result['stats'] = self._get_dashboard_stats()
        return result
