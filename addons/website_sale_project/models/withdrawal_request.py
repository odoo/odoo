# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose


class WithdrawalRequest(models.Model):
    _inherit = "withdrawal.request"

    project_id = fields.Many2one(
        comodel_name="project.project",
        string="Project",
        domain=[("is_template", "=", False)],
    )
    task_id = fields.Many2one(comodel_name="project.task")

    def _blacklisted_fields(self):
        return [*super()._blacklisted_fields(), "project_id", "task_id"]

    def _notify_withdrawal_request(self):
        """Notify the internal team that a withdrawal request was submitted.

        If a project is configured, a task is also created.
        """
        if self.project_id and self.project_id.id != 0:
            self.task_id = self.env["project.task"].sudo().create({
                "name": self.env._(
                    "Withdrawal Request %(order_reference)s", order_reference=self.order_reference,
                ),
                "project_id": self.project_id.id,
                "description": nl2br_enclose(self.log_message, "p"),
            })
        super()._notify_withdrawal_request()

    def _log_mail_sent_to_customer(self, mail_content):
        """Log the confirmation message sent to the customer on the task's chatter."""
        super()._log_mail_sent_to_customer(mail_content)
        if self.task_id:
            self.task_id.message_post(
                subject=mail_content["subject"],
                body=mail_content["body"],
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
