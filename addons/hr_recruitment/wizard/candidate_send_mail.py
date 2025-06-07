from odoo import api, fields, models, _


class CandidateSendMail(models.TransientModel):
    _name = "candidate.send.mail"
    _inherit = "mail.composer.mixin"
    _description = "Send mails to candidates"

    candidate_ids = fields.Many2many("hr.candidate", string="Candidates", required=True)
    author_id = fields.Many2one(
        "res.partner",
        "Author",
        required=True,
        default=lambda self: self.env.user.partner_id.id,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Attachments", readonly=False, store=True
    )

    @api.depends("subject")
    def _compute_render_model(self):
        self.render_model = "hr.candidate"

    def action_send(self):
        self.ensure_one()

        without_emails = self.candidate_ids.filtered(
            lambda c: not c.email_from or (c.partner_id and not c.partner_id.email)
        )
        if without_emails:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "danger",
                    "message": _(
                        "The following candidates are missing an email address: %s.",
                        ", ".join(
                            without_emails.mapped(
                                lambda c: c.partner_name or c.display_name
                            )
                        ),
                    ),
                },
            }

        if self.template_id:
            subjects = self.template_id._render_field(
                "subject", res_ids=self.candidate_ids.ids
            )
        else:
            subjects = {candidate.id: self.subject for candidate in self.candidate_ids}

        for candidate in self.candidate_ids:
            if not candidate.partner_id:
                candidate.partner_id = self.env["res.partner"].create(
                    {
                        "is_company": False,
                        "name": candidate.partner_name,
                        "email": candidate.email_from,
                        "phone": candidate.partner_phone,
                        "mobile": candidate.partner_phone,
                    }
                )

            attachment_ids = []
            for attachment_id in self.attachment_ids:
                new_attachment = attachment_id.copy(
                    {"res_model": "hr.candidate", "res_id": candidate.id}
                )
                attachment_ids.append(new_attachment.id)

            candidate.message_post(
                author_id=self.author_id.id,
                body=self.body,
                email_layout_xmlid="mail.mail_notification_light",
                message_type="comment",
                partner_ids=candidate.partner_id.ids,
                subject=subjects[candidate.id],
                attachment_ids=attachment_ids,
            )
