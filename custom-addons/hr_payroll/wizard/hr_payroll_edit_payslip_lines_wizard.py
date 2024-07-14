# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrPayrollEditPayslipLinesWizard(models.TransientModel):
    _name = 'hr.payroll.edit.payslip.lines.wizard'
    _description = 'Edit payslip lines wizard'

    payslip_id = fields.Many2one('hr.payslip', required=True, readonly=True)
    line_ids = fields.One2many('hr.payroll.edit.payslip.line', 'edit_payslip_lines_wizard_id', string='Payslip Lines')
    worked_days_line_ids = fields.One2many('hr.payroll.edit.payslip.worked.days.line', 'edit_payslip_lines_wizard_id', string='Worked Days Lines')

    def recompute_following_lines(self, line_id):
        self.ensure_one()
        wizard_line = self.env['hr.payroll.edit.payslip.line'].browse(line_id)
        reload_wizard = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.edit.payslip.lines.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
        if not wizard_line.salary_rule_id:
            return reload_wizard
        localdict = self.payslip_id._get_localdict()
        rules_dict = localdict['rules']
        result_rules_dict = localdict['result_rules']
        remove_lines = False
        lines_to_remove = []
        blacklisted_rule_ids = []
        for line in sorted(self.line_ids, key=lambda x: x.sequence):
            if remove_lines and line.code in self.payslip_id.line_ids.mapped('code'):
                lines_to_remove.append((2, line.id, 0))
            else:
                rules_dict[line.code] = line.salary_rule_id
                if line == wizard_line:
                    line._compute_total()
                    remove_lines = True
                blacklisted_rule_ids.append(line.salary_rule_id.id)
                localdict[line.code] = line.total
                result_rules_dict[line.code] = {'total': line.total, 'amount': line.amount, 'quantity': line.quantity, 'rate': line.rate}
                localdict = line.salary_rule_id.category_id._sum_salary_rule_category(localdict, line.total)

        payslip = self.payslip_id.with_context(force_payslip_localdict=localdict, prevent_payslip_computation_line_ids=blacklisted_rule_ids)
        self.line_ids = lines_to_remove + [(0, 0, line) for line in payslip._get_payslip_lines()]
        return reload_wizard

    def recompute_worked_days_lines(self):
        self.ensure_one()
        total_amount = sum(l.amount for l in self.worked_days_line_ids)
        lines = sorted(self.line_ids, key=lambda x: x.sequence)
        if not lines:
            return False
        lines[0].update({
            'amount': total_amount,
            'rate': 100,
            'quantity': 1,
        })
        return self.recompute_following_lines(lines[0].id)

    def action_validate_edition(self):
        today = fields.Date.today()
        self.mapped('payslip_id.line_ids').unlink()
        self.mapped('payslip_id.worked_days_line_ids').unlink()
        for wizard in self:
            lines = [(0, 0, line) for line in wizard.line_ids._export_to_payslip_line()]
            worked_days_lines = [(0, 0, line) for line in wizard.worked_days_line_ids._export_to_worked_days_line()]
            wizard.payslip_id.with_context(payslip_no_recompute=True).write({
                'edited': True,
                'line_ids': lines,
                'worked_days_line_ids': worked_days_lines,
                'compute_date': today
            })
            wizard.payslip_id.message_post(body=_('This payslip has been manually edited by %s.', self.env.user.name))


class HrPayrollEditPayslipLine(models.TransientModel):
    _name = 'hr.payroll.edit.payslip.line'
    _description = 'Edit payslip lines wizard line'

    name = fields.Char(translate=True)
    sequence = fields.Integer("Sequence")
    salary_rule_id = fields.Many2one(
        'hr.salary.rule', string='Rule',
        domain="[('struct_id', '=', struct_id)]")
    code = fields.Char(related='salary_rule_id.code')
    contract_id = fields.Many2one(related='slip_id.contract_id', string='Contract')
    employee_id = fields.Many2one(related='contract_id.employee_id', string='Employee')
    rate = fields.Float(string='Rate (%)', digits='Payroll Rate', default=100.0)
    amount = fields.Float(digits='Payroll')
    quantity = fields.Float(digits='Payroll', default=1.0)
    total = fields.Float(compute='_compute_total', string='Total', digits='Payroll', store=True)
    slip_id = fields.Many2one(related="edit_payslip_lines_wizard_id.payslip_id", string='Pay Slip')
    struct_id = fields.Many2one(related="slip_id.struct_id")
    category_id = fields.Many2one(related='salary_rule_id.category_id', readonly=True, store=True)

    edit_payslip_lines_wizard_id = fields.Many2one('hr.payroll.edit.payslip.lines.wizard', required=True, ondelete='cascade')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    def _export_to_payslip_line(self):
        return [{
            'sequence': line.sequence,
            'code': line.code,
            'name': line.name,
            'salary_rule_id': line.salary_rule_id.id,
            'contract_id': line.contract_id.id,
            'employee_id': line.employee_id.id,
            'amount': line.amount,
            'quantity': line.quantity,
            'rate': line.rate,
            'total': line.total,
            'slip_id': line.slip_id.id
        } for line in self]

class HrPayrollEditPayslipWorkedDaysLine(models.TransientModel):
    _name = 'hr.payroll.edit.payslip.worked.days.line'
    _description = 'Edit payslip line wizard worked days'

    name = fields.Char(related='work_entry_type_id.name')
    slip_id = fields.Many2one(related="edit_payslip_lines_wizard_id.payslip_id", string='PaySlip')
    sequence = fields.Integer("Sequence")
    code = fields.Char(related='work_entry_type_id.code')
    work_entry_type_id = fields.Many2one('hr.work.entry.type')
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    amount = fields.Float(string='Amount')

    edit_payslip_lines_wizard_id = fields.Many2one('hr.payroll.edit.payslip.lines.wizard', required=True, ondelete='cascade')

    def _export_to_worked_days_line(self):
        return [{
            'name': line.name,
            'sequence': line.sequence,
            'code': line.code,
            'work_entry_type_id': line.work_entry_type_id.id,
            'number_of_days': line.number_of_days,
            'number_of_hours': line.number_of_hours,
            'amount': line.amount,
            'payslip_id': line.slip_id.id
        } for line in self]
