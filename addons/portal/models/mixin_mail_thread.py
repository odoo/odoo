import hashlib
import hmac

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.mail.tools.discuss import EMPTY_EDIT_MARKER
from odoo.addons.portal.utils import (
    is_thread_hash_pid_valid,
    is_thread_token_valid,
    resolve_thread_for_credentials,
)


class MixinMailThread(models.AbstractModel):
    _inherit = "mixin.mail.thread"

    _mail_post_token_field = "access_token"

    website_message_ids = fields.One2many(
        comodel_name="mail.message",
        inverse_name="res_id",
        string="Portal Messages",
        domain=lambda self: [
            ("model", "=", self._name),
            (
                "message_type",
                "in",
                ("comment", "email", "email_outgoing", "auto_comment", "out_of_office"),
            ),
        ],
        bypass_search_access=True,
        help="Portal communication history for this record.",
    )

    def _get_domain_portal_message_fetch(self, message_domain=None):
        MailMessage = self.env["mail.message"]
        field = self._fields["website_message_ids"]
        if message_domain is None:
            message_domain = self._get_domain_portal_message_non_empty()
        return (
            Domain(field.get_comodel_domain(self))
            & Domain("res_id", "in", self.ids)
            & Domain(MailMessage._get_search_domain_share())
            & Domain(message_domain)
        )

    def _get_domain_portal_message_non_empty(self):
        return Domain("body", "not in", [False, EMPTY_EDIT_MARKER]) | Domain(
            "attachment_ids", "!=", False
        )

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        portal_enabled = isinstance(self, self.env.registry["mixin.portal"])
        if not portal_enabled:
            return groups

        customer = self._mail_get_partners(introspect_fields=False)[self.id]
        if customer:
            access_token = self.sudo()._portal_get_or_create_token()
            local_msg_vals = dict(msg_vals or {})
            local_msg_vals["access_token"] = access_token
            local_msg_vals["pid"] = customer.id
            local_msg_vals["hash"] = self._sign_token(customer.id)
            local_msg_vals.update(customer.sudo().signup_get_auth_param()[customer.id])
            access_link = self._notify_get_action_link("view", **local_msg_vals)

            new_group = [
                (
                    "portal_customer",
                    lambda pdata: pdata["id"] == customer.id,
                    {
                        "active": True,
                        "button_access": {
                            "url": access_link,
                        },
                        "has_button_access": True,
                    },
                )
            ]
        else:
            new_group = []

        portal_group = next((g for g in groups if g[0] == "portal"), None)
        if portal_group is not None:
            portal_group[2]["active"] = True
            portal_group[2]["has_button_access"] = True

        return new_group + groups

    def _sign_token(self, pid) -> str:
        self.check_singleton()
        if self._mail_post_token_field not in self._fields:
            raise NotImplementedError(
                f"Model {self._name} does not support token signature, as it does "
                f"not have {self._mail_post_token_field} field."
            )
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret")
        token = (self.env.cr.dbname, self[self._mail_post_token_field], pid)
        return hmac.new(
            secret.encode(), repr(token).encode(), hashlib.sha256
        ).hexdigest()

    def _portal_get_parent_hash_token(self, pid):
        return False

    @api.model
    def _get_allowed_access_params(self):
        return super()._get_allowed_access_params() | {"hash", "pid", "token"}

    @api.model
    def _get_thread_with_access(
        self, thread_id, *, hash=None, pid=None, token=None, **kwargs
    ):
        if thread := super()._get_thread_with_access(
            thread_id, hash=hash, pid=pid, token=token, **kwargs
        ):
            return thread
        thread = resolve_thread_for_credentials(self.browse(thread_id).sudo())
        if thread and (
            is_thread_hash_pid_valid(thread, hash, pid)
            or is_thread_token_valid(thread, token)
        ):
            return thread
        return self.browse()
