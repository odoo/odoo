# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosEmailPrintWizard(models.TransientModel):
    _name = "pos.email.print.wizard"
    _description = "Selection of printers"

    selected_email_ids = fields.Many2many("pos.report_email_printer_email")
    report_printer_email_ids = fields.Many2many("pos.report_email_printer_email", relation="report_printer_email_id_pos_email_print_wizard")

    def send_emails(self):
        report = self.env["ir.actions.report"].browse(self.env.context["report_id"])
        emails = self.selected_email_ids.mapped("email")
        report._send_report_email(self.env.context["res_ids"], self.env.context["data"], emails)
        return {"type": "ir.actions.act_window_close"}
