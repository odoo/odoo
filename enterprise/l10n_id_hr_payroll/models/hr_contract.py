# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Contract(models.Model):
    _inherit = "hr.contract"

    l10n_id_bpjs_jkk = fields.Float(string="BPJS JKK(%)")

    def l10n_id_action_view_historical_lines(self):
        """ As the historical payslip line values of 'GROSS' and 'PPH21' is used to calculate
        for the end of year/contract payment, HR team likes to cross-check the values manually

        Show all payslip lines that are in validated/paid for code: 'GROSS" or 'PPH21'"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.act_contribution_reg_payslip_lines")
        action.update(
            {
                'domain': [('contract_id', '=', self.id), ('code', 'in', ('GROSS', 'PPH21'))],
                'context': "{'search_default_category_id': 1}",
                'views': [(self.env.ref('l10n_id_hr_payroll.hr_payslip_line_view_tree_id_history').id, 'list'), (False, 'form')]
            }
        )
        return action
