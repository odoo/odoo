# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class HrContract(models.Model):
    """
    Employee contract allows to add different values in fields.
    Fields are used in salary rule computation.
    """
    _inherit = 'hr.contract'

    tds = fields.Float(string='TDS', digits=dp.get_precision('Payroll'),
        help='Amount for Tax Deduction at Source')
    driver_salay = fields.Boolean(string='Driver Salary', help='Check this box if you provide allowance for driver')
    medical_insurance = fields.Float(string='Medical Insurance', digits=dp.get_precision('Payroll'),
        help='Deduction towards company provided medical insurance')
    voluntary_provident_fund = fields.Float(string='Voluntary Provident Fund (%)', digits=dp.get_precision('Payroll'),
        help='VPF is a safe option wherein you can contribute more than the PF ceiling of 12% that has been mandated by the government and VPF computed as percentage(%)')
    house_rent_allowance_metro_nonmetro = fields.Float(string='House Rent Allowance (%)', digits=dp.get_precision('Payroll'),
        help='HRA is an allowance given by the employer to the employee for taking care of his rental or accommodation expenses for metro city it is 50% and for non metro 40%. \nHRA computed as percentage(%)')
    supplementary_allowance = fields.Float(string='Supplementary Allowance', digits=dp.get_precision('Payroll'))


class HrPayrollAdvice(models.Model):
    '''
    Bank Advice
    '''
    _name = 'hr.payroll.advice'
    _description = "Indian HR Payroll Advice"

    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    name = fields.Char(readonly=True, required=True, states={'draft': [('readonly', False)]})
    note = fields.Text(string='Description', default='Please make the payroll transfer from above account number to the below mentioned account numbers towards employee salaries:')
    date = fields.Date(readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_get_default_date,
        help='Advice Date is used to search Payslips')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', index=True, readonly=True)
    number = fields.Char(string='Reference', readonly=True)
    line_ids = fields.One2many('hr.payroll.advice.line', 'advice_id', string='Employee Salary',
        states={'draft': [('readonly', False)]}, readonly=True, copy=True)
    chaque_nos = fields.Char(string='Cheque Numbers')
    neft = fields.Boolean(string='NEFT Transaction', help='Check this box if your company use online transfer for salary')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, states={'draft': [('readonly', False)]},
        help='Select the Bank from which the salary is going to be paid')
    batch_id = fields.Many2one('hr.payslip.run', string='Batch', readonly=True)

    @api.multi
    def compute_advice(self):
        """
        Advice - Create Advice lines in Payment Advice and
        compute Advice lines.
        """
        for advice in self:
            old_lines = self.env['hr.payroll.advice.line'].search([('advice_id', '=', advice.id)])
            if old_lines:
                old_lines.unlink()
            payslips = self.env['hr.payslip'].search([('date_from', '<=', advice.date), ('date_to', '>=', advice.date), ('state', '=', 'done')])
            for slip in payslips:
                if not slip.employee_id.bank_account_id and not slip.employee_id.bank_account_id.acc_number:
                    raise UserError(_('Please define bank account for the %s employee') % (slip.employee_id.name,))
                payslip_line = self.env['hr.payslip.line'].search([('slip_id', '=', slip.id), ('code', '=', 'NET')], limit=1)
                if payslip_line:
                    self.env['hr.payroll.advice.line'].create({
                        'advice_id': advice.id,
                        'name': slip.employee_id.bank_account_id.acc_number,
                        'ifsc_code': slip.employee_id.bank_account_id.bank_bic or '',
                        'employee_id': slip.employee_id.id,
                        'bysal': payslip_line.total
                    })
                slip.advice_id = advice.id

    @api.multi
    def confirm_sheet(self):
        """
        confirm Advice - confirmed Advice after computing Advice Lines..
        """
        for advice in self:
            if not advice.line_ids:
                raise UserError(_('You can not confirm Payment advice without advice lines.'))
            date = fields.Date.from_string(fields.Date.today())
            advice_year = date.strftime('%m') + '-' + date.strftime('%Y')
            number = self.env['ir.sequence'].next_by_code('payment.advice')
            advice.write({
                'number': 'PAY' + '/' + advice_year + '/' + number,
                'state': 'confirm',
            })

    @api.multi
    def set_to_draft(self):
        """Resets Advice as draft.
        """
        self.write({'state': 'draft'})

    @api.multi
    def cancel_sheet(self):
        """Marks Advice as cancelled.
        """
        self.write({'state': 'cancel'})

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.bank_id = self.company_id.partner_id.bank_ids and self.company_id.partner_id.bank_ids[0].bank_id.id or False


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    _description = 'Payslip Batches'

    available_advice = fields.Boolean(string='Made Payment Advice?',
                                       help='If this box is checked which means that Payment Advice exists for current batch',
                                       readonly=False, copy=False)

    @api.multi
    def draft_payslip_run(self):
        super(HrPayslipRun, self).draft_payslip_run()
        self.write({'available_advice': False})

    @api.multi
    def create_advice(self):
        for run in self:
            if run.available_advice:
                raise UserError(_("Payment advice already exists for %s, 'Set to Draft' to create a new advice.") % (run.name,))
            company = self.env.user.company_id
            advice = self.env['hr.payroll.advice'].create({
                        'batch_id': run.id,
                        'company_id': company.id,
                        'name': run.name,
                        'date': run.date_end,
                        'bank_id': company.partner_id.bank_ids and company.partner_id.bank_ids[0].bank_id.id or False
                    })
            for slip in run.slip_ids:
                # TODO is it necessary to interleave the calls ?
                slip.action_payslip_done()
                if not slip.employee_id.bank_account_id or not slip.employee_id.bank_account_id.acc_number:
                    raise UserError(_('Please define bank account for the %s employee') % (slip.employee_id.name))
                payslip_line = self.env['hr.payslip.line'].search([('slip_id', '=', slip.id), ('code', '=', 'NET')], limit=1)
                if payslip_line:
                    self.env['hr.payroll.advice.line'].create({
                        'advice_id': advice.id,
                        'name': slip.employee_id.bank_account_id.acc_number,
                        'ifsc_code': slip.employee_id.bank_account_id.bank_bic or '',
                        'employee_id': slip.employee_id.id,
                        'bysal': payslip_line.total
                    })
        self.write({'available_advice': True})


class HrPayrollAdviceLine(models.Model):
    '''
    Bank Advice Lines
    '''
    _name = 'hr.payroll.advice.line'
    _description = 'Bank Advice Lines'

    advice_id = fields.Many2one('hr.payroll.advice', string='Bank Advice')
    name = fields.Char('Bank Account No.', required=True)
    ifsc_code = fields.Char(string='IFSC Code')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    bysal = fields.Float(string='By Salary', digits=dp.get_precision('Payroll'))
    debit_credit = fields.Char(string='C/D', default='C')
    company_id = fields.Many2one('res.company', related='advice_id.company_id', string='Company', store=True, readonly=False)
    ifsc = fields.Boolean(related='advice_id.neft', string='IFSC', readonly=False)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.name = self.employee_id.bank_account_id.acc_number
        self.ifsc_code = self.employee_id.bank_account_id.bank_bic or ''


class HrPayslip(models.Model):
    '''
    Employee Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slips'

    advice_id = fields.Many2one('hr.payroll.advice', string='Bank Advice', copy=False)


class ResCompany(models.Model):
    _inherit = 'res.company'

    dearness_allowance = fields.Boolean(string='Dearness Allowance', default=True,
        help='Check this box if your company provide Dearness Allowance to employee')
