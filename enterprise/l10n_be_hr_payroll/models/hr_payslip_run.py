#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'


    l10n_be_display_eco_voucher_button = fields.Boolean(
        compute='_compute_l10n_be_display_eco_voucher_button')

    @api.depends('slip_ids')
    def _compute_l10n_be_display_eco_voucher_button(self):
        # Display button if batch is from belgium with out
        # employees
        for batch in self:
            if batch.company_id.country_id.code != "BE" or \
                    all(slip.struct_id.code != 'CP200HOLN' and slip.state != 'cancel' for slip in batch.slip_ids):
                batch.l10n_be_display_eco_voucher_button = False
            else:
                batch.l10n_be_display_eco_voucher_button = True


    def action_l10n_be_eco_vouchers(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('l10n_be_hr_payroll.l10n_be_eco_vouchers_wizard_action')
        out_employees = self.slip_ids.filtered(lambda s: s.struct_id.code == 'CP200HOLN').employee_id
        res['context'] = {
            'employee_ids': out_employees.ids,
            'batch_id': self.id,
        }
        return res
