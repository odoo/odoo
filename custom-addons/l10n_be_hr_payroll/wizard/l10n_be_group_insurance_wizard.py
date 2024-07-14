# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nBeGroupInsuranceWizard(models.TransientModel):
    _name = 'l10n.be.group.insurance.wizard'
    _description = 'Group Insurance Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    date_from = fields.Date(default=lambda self: fields.Date.today() + relativedelta(day=1, month=1))
    date_to = fields.Date(default=lambda self: fields.Date.today() + relativedelta(day=31, month=12))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many(
        'l10n.be.group.insurance.line.wizard', 'wizard_id',
        compute='_compute_line_ids', store=True, readonly=False)

    @api.depends('date_from', 'date_to')
    def _compute_line_ids(self):
        for wizard in self.filtered(lambda w: w.date_from and w.date_to):
            all_payslips = self.env['hr.payslip'].search([
                ('company_id', '=', wizard.company_id.id),
                ('date_from', '>=', wizard.date_from),
                ('date_to', '<=', wizard.date_to),
                ('state', 'in', ['done', 'paid'])
            ])
            line_values = all_payslips._get_line_values(
                ['GROUPINSURANCE'],
                vals_list=['amount']
            )
            employees_amount = defaultdict(lambda: 0.0)
            for payslip in all_payslips:
                employees_amount[payslip.employee_id] += line_values['GROUPINSURANCE'][payslip.id]['amount']
            wizard.line_ids = [(0, 0, {
                'employee_id': employee.id,
                'amount': amount,
                'wizard_id': wizard.id,
            }) for employee, amount in employees_amount.items()]

    def action_export_xls(self):
        self.ensure_one()
        return {
            'name': 'Export Group Insurance Amount',
            'type': 'ir.actions.act_url',
            'url': '/export/group_insurance/%s' % (self.id),
        }

class L10nBeGroupInsuranceLineWizard(models.TransientModel):
    _name = 'l10n.be.group.insurance.line.wizard'
    _description = 'Group Insurance Wizard Line'

    wizard_id = fields.Many2one('l10n.be.group.insurance.wizard')
    employee_id = fields.Many2one('hr.employee', required=True)
    niss = fields.Char(string="NISS", related='employee_id.niss')
    amount = fields.Monetary()
    currency_id = fields.Many2one(related='wizard_id.currency_id')
