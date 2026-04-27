from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError


class L10nAuStpFfrWizard(models.TransientModel):
    _name = "l10n_au.stp.ffr.wizard"
    _description = "STP Full File Replacement Wizard"

    stp_id = fields.Many2one("l10n_au.stp", string="Report to Replace", required=True)
    ffr_payslip_ids = fields.One2many("l10n_au.stp.ffr.payslip", "ffr_wizard_id", string="Payslips")

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        stp = self.env["l10n_au.stp"].browse(res.get("stp_id"))
        res["ffr_payslip_ids"] = [
            Command.create({"payslip_id": slip.id}) for slip in stp.payslip_ids
        ]
        return res

    @api.constrains("stp_id")
    def _check_stp_status(self):
        for rec in self:
            if rec.stp_id.ffr:
                raise UserError(_("A submission can only be replaced once. Please use an update event for further modifications."))
            if rec.stp_id.state != "sent":
                raise UserError(_("STP must be submit state to create a full file replacement."))

    def action_create_ffr(self):
        self.ensure_one()
        payslips_to_reset = self.ffr_payslip_ids.filtered("to_reset").payslip_id
        if not self.env.user.has_group("hr_payroll.group_hr_payroll_manager"):
            raise UserError(_("Only payroll managers can create a full file replacement. Since it requires resetting payslips."))
        payslips_to_reset.sudo().action_payslip_cancel()
        payslips_to_reset.with_context(allow_ffr=True).action_payslip_draft()

        payslip_reset_message = _("Payslip(s) have been reset for Full File Replacement. "
                                  "Please verify the payslip batch before resubmitting.")
        for slip in payslips_to_reset:
            slip.message_post(subject="Single Touch Payroll", body=payslip_reset_message)

        if payslips_to_reset.payslip_run_id:
            payslips_to_reset.payslip_run_id.state = "verify"
            payslips_to_reset.payslip_run_id.message_post(subject="Single Touch Payroll", body=payslip_reset_message)
        payslips_to_reset.compute_sheet()
        self.stp_id.is_replaced = True
        new_stp = self.env["l10n_au.stp"].create({
            "company_id": self.stp_id.company_id.id,
            "payevent_type": "submit",
            "ffr": True,
            "previous_report_id": self.stp_id.id,
            "payslip_batch_id": self.stp_id.payslip_batch_id.id,
            "payslip_ids": [Command.set(self.ffr_payslip_ids.payslip_id.ids)],
        })
        return new_stp._get_records_action()


class L10nAuStpffrPayslip(models.TransientModel):
    _name = "l10n_au.stp.ffr.payslip"
    _description = "STP Full File Replacement Payslips"

    ffr_wizard_id = fields.Many2one("l10n_au.stp.ffr.wizard", string="Wizard", required=True, ondelete="cascade")
    payslip_id = fields.Many2one("hr.payslip", string="Payslip", readonly=True, required=True)
    to_reset = fields.Boolean(
        "Reset Payslip",
        default=True,
        help="Check this box to reset the payslip, to be modified before resubmitting.",
    )
