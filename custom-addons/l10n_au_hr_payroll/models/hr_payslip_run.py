# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    l10n_au_export_aba_file = fields.Binary(
        string="ABA File",
        readonly=True,
        copy=False,
        help="Export ABA file for this payslip run")
    l10n_au_export_aba_filename = fields.Char(
        string="ABA File Name",
        copy=False,
        help="Name of the export ABA file for this payslip run")

    def action_open_aba_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate ABA File."),
            "res_model": "hr.payslip.run.aba.wizard",
            "view_mode": "form",
            "view_id": "hr_payslip_run_aba_view_form",
            "views": [(False, "form")],
            "target": "new",
        }
