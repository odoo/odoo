# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipRunHsbcAutopayWizard(models.TransientModel):
    _name = 'hr.payslip.run.aba.wizard'
    _description = 'HR Payslip Run ABA Wizard'

    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    def generate_aba_file(self):
        payslip_run_id = self.env['hr.payslip.run'].browse(self.env.context['active_id'])
        payslips = payslip_run_id.slip_ids.filtered(lambda p: p.net_wage > 0)
        payslips.sudo()._generate_aba_file(self.journal_id)
