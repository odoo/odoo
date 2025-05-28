from odoo import fields, models
from odoo.exceptions import UserError
from odoo.addons.mail.tools.parser import parse_res_ids


class MailFollowersEdit(models.TransientModel):
    """Wizard to edit partners (or channels) to add/remove them to/from followers list."""

    _name = 'mail.followers.edit'
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
    partner_ids = fields.Many2many("res.partner", required=True, string="Followers")
    message = fields.Html("Message")
    notify = fields.Boolean("Notify Recipients", default=False)

    def edit_followers(self):
        for wizard in self:
            res_ids = parse_res_ids(wizard.res_ids, self.env)
            documents = self.env[wizard.res_model].browse(res_ids)
            if not documents:
                raise UserError(self.env._("No documents found for the selected records."))
            if wizard.operation == "remove":
                documents.message_unsubscribe(partner_ids=wizard.partner_ids.ids)
            else:
                if not self.env.user.email:
                    raise UserError(
                        self.env._(
                            "Unable to post message, please configure the sender's email address."
                        )
                    )
                documents.message_subscribe(partner_ids=wizard.partner_ids.ids)
                if wizard.notify:
                    model_name = self.env["ir.model"]._get(wizard.res_model).display_name
                    message_values = wizard._prepare_message_values(documents, model_name)
                    message_values["partner_ids"] = wizard.partner_ids.ids
                    documents[0].message_notify(**message_values)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
            "type": "success",
            "message": self.env._("Followers updated") if len(wizard) > 1 else (
                self.env._("Followers added") if wizard.operation == "add" else self.env._("Followers removed")
            ),
            "sticky": False,
            "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _prepare_message_values(self, documents, model_name):
        return {
            "body": (len(documents) > 1 and (", ".join(documents.mapped('display_name')) + "\n") or "") + (self.message or ""),
            "email_add_signature": False,
            "email_from": self.env.user.email_formatted,
            "email_layout_xmlid": len(documents) > 1 and "mail.mail_notification_multi_invite" or "mail.mail_notification_invite",
            "model": self.res_model,
            "reply_to": self.env.user.email_formatted,
            "reply_to_force_new": True,
            "subject": len(documents) > 1 and self.env._(
                "Invitation to follow %(document_model)s.",
                document_model=model_name,
            ) or self.env._(
                "Invitation to follow %(document_model)s: %(document_name)s",
                document_model=model_name,
                document_name=documents.display_name,
            )
        }
