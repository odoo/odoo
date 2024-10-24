from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.mail.tools.parser import parse_res_ids


class MailFollowersEdit(models.TransientModel):
    """Wizard to edit partners (or channels) to add/remove them to/from followers list."""

    _description = "Followers edit wizard"

    res_model = fields.Char(
        "Related Document Model", required=True, help="Model of the followed resource"
    )
    res_ids = fields.Char("Related Document IDs", help="Ids of the followed resources")
    operation = fields.Selection(
        [
            ("add", "Add"),
            ("remove", "Remove"),
        ],
        string="Operation",
        required=True,
        default="add",
    )
    partner_ids = fields.Many2many("res.partner", string="Recipients")
    message = fields.Html("Message")
    notify = fields.Boolean("Notify Recipients", default=True)

    def edit_followers(self):
        for wizard in self:
            res_ids = parse_res_ids(wizard.res_ids, self.env)
            documents = self.env[wizard.res_model].browse(res_ids)
            if wizard.operation == "remove":
                for document in documents:
                    document.message_unsubscribe(partner_ids=wizard.partner_ids.ids)
            else:
                if not self.env.user.email:
                    raise UserError(
                        _("Unable to post message, please configure the sender's email address.")
                    )
                for document in documents:
                    # filter partner_ids to get the new followers, to avoid sending email to already following partners
                    new_partners = wizard.partner_ids - document.sudo().message_partner_ids
                    if not new_partners:
                        continue
                    document.message_subscribe(partner_ids=new_partners.ids)
                    if wizard.notify:
                        model_name = self.env["ir.model"]._get(wizard.res_model).display_name
                        message_values = wizard._prepare_message_values(document, model_name)
                        message_values["partner_ids"] = new_partners.ids
                        document.message_notify(**message_values)
        return {"type": "ir.actions.act_window_close"}

    def _prepare_message_values(self, document, model_name):
        return {
            "body": self.message or "",
            "email_add_signature": False,
            "email_from": self.env.user.email_formatted,
            "email_layout_xmlid": "mail.mail_notification_invite",
            "model": self.res_model,
            "record_name": document.display_name,
            "reply_to": self.env.user.email_formatted,
            "reply_to_force_new": True,
            "subject": _(
                "Invitation to follow %(document_model)s: %(document_name)s",
                document_model=model_name,
                document_name=document.display_name,
            ),
        }
