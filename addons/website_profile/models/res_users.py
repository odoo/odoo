import hashlib
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq

_debug = DebugLog(__name__)

VALIDATION_KARMA_GAIN = 3
VALIDATION_EMAIL_COOLDOWN = timedelta(seconds=60)


class ResUsers(models.Model):
    _inherit = "res.users"

    profile_validation_email_last_sent = fields.Datetime(copy=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["karma"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "country_id",
            "city",
            "website",
            "website_description",
            "website_published",
        ]

    def write(self, vals):
        if "country_id" in vals and self == self.env.user:
            for user in self:
                if (
                    not user.partner_id._can_edit_country()
                    and vals["country_id"] != user.partner_id.country_id.id
                ):
                    _debug.logic(
                        "profile_country_refused", reason="not_editable", user=user.id
                    )
                    raise UserError(
                        _(
                            "Changing the country is not allowed once document(s) "
                            "have been issued for your account. Please contact us "
                            "directly for this operation."
                        )
                    )
        return super().write(vals)

    @api.model
    def _generate_profile_token(self, user_id, email):
        profile_uuid = (
            self.env["ir.config_parameter"].sudo().get_param("website_profile.uuid")
        )
        if not profile_uuid:
            profile_uuid = str(uuid.uuid4())
            self.env["ir.config_parameter"].sudo().set_param(
                "website_profile.uuid", profile_uuid
            )
        return hashlib.sha256(
            (
                "%s-%s-%s-%s"
                % (
                    datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                    profile_uuid,
                    user_id,
                    email,
                )
            ).encode("utf-8")
        ).hexdigest()

    def _send_profile_validation_email(self, **kwargs):
        if not self.email:
            return False
        now = fields.Datetime.now()
        last_sent = self.profile_validation_email_last_sent
        if last_sent and now - last_sent < VALIDATION_EMAIL_COOLDOWN:
            _debug.logic("validation_email_throttled", user=self.id)
            return False
        self.sudo().profile_validation_email_last_sent = now
        token = self._generate_profile_token(self.id, self.email)
        activation_template = self.env.ref("website_profile.validation_email")
        if activation_template:
            params = {"token": token, "user_id": self.id, "email": self.email}
            params.update(kwargs)
            token_url = self.get_base_url() + "/profile/validate_email?%s" % urlencode(
                params
            )
            activation_template.sudo().with_context(token_url=token_url).send_mail(
                self.id, force_send=True, raise_exception=True
            )
        return True

    def _process_profile_validation_token(self, token, email):
        self.check_singleton()
        validation_token = self._generate_profile_token(self.id, email)
        if consteq(token, validation_token) and self.karma == 0:
            return self.write({"karma": VALIDATION_KARMA_GAIN})
        return False
