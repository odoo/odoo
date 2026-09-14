import re

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.sms_twilio.tools.sms_api import SmsApiTwilio


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "sms_twilio_auth_token": "sms_twilio_auth_token",
    }

    sms_provider = fields.Selection(
        selection=[
            ("iap", "Send via Odoo"),
            ("twilio", "Send via Twilio"),
        ],
        string="SMS Provider",
        default="iap",
    )
    sms_twilio_account_sid = fields.Char(
        string="Account SID",
        groups="base.group_system",
    )
    sms_twilio_auth_token = fields.Char(
        string="Auth Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
    sms_twilio_number_ids = fields.One2many(
        comodel_name="sms.twilio.number",
        inverse_name="company_id",
        string="Numbers",
    )

    def _get_sms_api_class(self):
        self.check_singleton()
        if self.sms_provider == "twilio":
            return SmsApiTwilio
        return super()._get_sms_api_class()

    def _assert_twilio_sid(self):
        self.check_singleton()
        account_sid = self.sms_twilio_account_sid
        if (
            not account_sid
            or len(account_sid) != 34
            or not account_sid.startswith("AC")
        ):
            raise UserError(
                _(
                    "Invalid Twilio Account SID: must start with 'AC' and be 34 characters long."
                )
            )
        if not re.match(r"^[A-Za-z0-9]{32}$", account_sid[2:]):
            raise UserError(
                _(
                    "Invalid Twilio Account SID: must only contain alphanumeric characters after 'AC'."
                )
            )

    def _action_view_sms_twilio_account_manage(self):
        return {
            "name": _("Manage Twilio SMS"),
            "res_model": "sms.twilio.account.manage",
            "res_id": False,
            "context": self.env.context,
            "type": "ir.actions.act_window",
            "views": [(False, "form")],
            "view_mode": "form",
            "target": "new",
        }
