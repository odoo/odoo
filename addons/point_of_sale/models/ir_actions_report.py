# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrActionReport(models.Model):
    _inherit = "ir.actions.report"

    report_email_printer_id = fields.One2many("pos.report_email_printer", "report_id")

    def report_action(self, docids, data=None, config=True):
        result = super().report_action(docids, data, config)
        if result.get('type') != 'ir.actions.report':
            return result
        if self.report_email_printer_id:
            result["printer_emails"] = self.report_email_printer_id.email_ids.mapped("email")
            result["id"] = self.id

        return result

    def get_email_selection_wizard(self, res_ids, data=None):
        wizard = self.env["pos.email.print.wizard"].create({
            "report_printer_email_ids": self.report_email_printer_id.email_ids.ids,
        })
        return {
            "name": "Select printers",
            "res_id": wizard.id,
            "type": "ir.actions.act_window",
            "res_model": "pos.email.print.wizard",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "data": data,
                "res_ids": res_ids,
                "report_id": self.id,
            },
        }

    def _create_pdf_attachment(self, pdf_content):
        return self.env["ir.attachment"].sudo().create({
            "name": f"{self.name}.pdf",
            "raw": pdf_content,
            "res_model": self.model,
            "type": "binary",
            "mimetype": "application/pdf"
        })

    def _send_report_email(self, res_ids, data, emails):
        report_content, report_type = self._render(self, res_ids, data)
        attachment = None
        body_html = None
        if report_type == "pdf":
            attachment = self._create_pdf_attachment(report_content)
        else:
            body_html = report_content

        self.env["mail.mail"].sudo().create({
            "body_html": body_html,
            "author_id": self.env.user.partner_id.id,
            "email_from": self.env.user.email_formatted,
            "email_to": ",".join(emails),
            "subject": self.name,
            "attachment_ids": [attachment.id] if attachment else None
        }).send(raise_exception=True)

    def send_report_to_linked_emails(self, res_ids, data=None):
        emails = self.report_email_printer_id.email_ids.mapped("email")
        self._send_report_email(res_ids, data, emails)
