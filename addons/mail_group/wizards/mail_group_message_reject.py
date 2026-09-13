from odoo import _, api, fields, models, tools


class MailGroupMessageReject(models.TransientModel):
    _name = "mail.group.message.reject"
    _description = "Reject Group Message"

    subject = fields.Char(
        compute="_compute_subject",
        store=True,
        readonly=False,
    )
    body = fields.Html(
        string="Contents",
        sanitize_style=True,
        default="",
    )
    email_from_normalized = fields.Char(
        related="mail_group_message_id.email_from_normalized",
        string="Email From",
    )
    mail_group_message_id = fields.Many2one(
        comodel_name="mail.group.message",
        string="Message",
        readonly=True,
        required=True,
    )
    action = fields.Selection(
        selection=[("reject", "Reject"), ("ban", "Ban")],
        required=True,
    )

    send_email = fields.Boolean(
        compute="_compute_send_email",
        help="Send an email to the author of the message",
    )

    @api.depends("mail_group_message_id")
    def _compute_subject(self):
        for wizard in self:
            wizard.subject = _("Re: %s", wizard.mail_group_message_id.subject or "")

    @api.depends("body")
    def _compute_send_email(self):
        for wizard in self:
            wizard.send_email = not tools.is_html_empty(wizard.body)

    def action_send_mail(self):
        self.check_singleton()

        if self.action == "reject" and self.send_email:
            self.mail_group_message_id.action_moderate_reject_with_comment(
                self.subject, self.body
            )
        elif self.action == "reject" and not self.send_email:
            self.mail_group_message_id.action_moderate_reject()

        elif self.action == "ban" and self.send_email:
            self.mail_group_message_id.action_moderate_ban_with_comment(
                self.subject, self.body
            )
        elif self.action == "ban" and not self.send_email:
            self.mail_group_message_id.action_moderate_ban()
