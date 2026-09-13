import typing

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.parser import parse_res_ids

if typing.TYPE_CHECKING:
    from ..models.res_partner import ResPartner

_debug = DebugLog(__name__)


class MailFollowersEdit(models.TransientModel):
    _name = "mail.followers.edit"
    _description = "Followers edit wizard"

    res_model = fields.Char(
        string="Related Document Model",
        required=True,
        help="Model of the followed resource",
    )
    res_ids = fields.Char(
        string="Related Document IDs",
        help="Ids of the followed resources",
    )
    operation = fields.Selection(
        selection=[
            ("add", "Add"),
            ("remove", "Remove"),
        ],
        default="add",
        required=True,
    )
    partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        string="Followers",
        required=True,
    )
    message = fields.Html()
    notify = fields.Boolean(
        string="Notify Recipients",
        default=False,
    )

    def edit_followers(self) -> dict:
        for wizard in self:
            res_ids = parse_res_ids(wizard.res_ids, self.env)
            documents = self.env[wizard.res_model].browse(res_ids).exists()
            if not documents:
                raise UserError(
                    self.env._("No documents found for the selected records.")
                )
            _debug.lifecycle(
                "followers_edited",
                wizard=wizard.id,
                model=wizard.res_model,
                documents=len(documents),
                partners=len(wizard.partner_ids),
                operation=wizard.operation,
                notify=wizard.notify,
            )
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
                    model_name = (
                        self.env["ir.model"]._get(wizard.res_model).display_name
                    )
                    message_values = wizard._prepare_message_values(
                        documents, model_name
                    )
                    message_values["partner_ids"] = wizard.partner_ids.ids
                    documents[0].message_notify(**message_values)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self._get_notification_message(),
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_notification_message(self) -> str:
        if len(self) != 1:
            return self.env._("Followers updated")
        if self.operation == "add":
            return self.env._("Followers added")
        return self.env._("Followers removed")

    def _prepare_message_values(
        self, documents: models.BaseModel, model_name: str
    ) -> dict:
        return {
            "body": (
                (
                    len(documents) > 1
                    and (", ".join(documents.mapped("display_name")) + "\n")
                )
                or ""
            )
            + (self.message or ""),
            "email_add_signature": False,
            "email_from": self.env.user.email_formatted,
            "email_layout_xmlid": (
                len(documents) > 1 and "mail.mail_notification_multi_invite"
            )
            or "mail.mail_notification_invite",
            "model": self.res_model,
            "reply_to": self.env.user.email_formatted,
            "reply_to_force_new": True,
            "subject": (
                len(documents) > 1
                and self.env._(
                    "Invitation to follow %(document_model)s.",
                    document_model=model_name,
                )
            )
            or self.env._(
                "Invitation to follow %(document_model)s: %(document_name)s",
                document_model=model_name,
                document_name=documents.display_name,
            ),
        }
