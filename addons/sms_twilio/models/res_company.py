import re

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.sms_twilio.tools.sms_api import SmsApiTwilio


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "sms_twilio_auth_token": "sms_twilio_auth_token",
    }

    sms_twilio_config_id = fields.Many2one(
        comodel_name="sms_twilio.config",
        compute="_compute_sms_twilio_config_id",
        search="_search_sms_twilio_config_id",
    )

    sms_twilio_auth_token = fields.Char(
        string="Auth Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )

    # the company's own Twilio numbers, whose inverse names the company: a
    # collection it owns, not a setting the configuration keeps
    sms_twilio_number_ids = fields.One2many(
        comodel_name="sms.twilio.number",
        inverse_name="company_id",
        string="Numbers",
    )

    def _search_sms_twilio_config_id(self, operator, value):
        return self._search_config_link("sms_twilio.config", operator, value)

    def _compute_sms_twilio_config_id(self):
        configs = self.env["sms_twilio.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.sms_twilio_config_id = by_company.get(company.id, False)

    def _get_sms_api_class(self):
        self.check_singleton()
        if self.sms_twilio_config_id.sms_provider == "twilio":
            return SmsApiTwilio
        return super()._get_sms_api_class()

    def _assert_twilio_sid(self):
        self.check_singleton()
        account_sid = self.sms_twilio_config_id.sms_twilio_account_sid
        if (
            not account_sid
            or len(account_sid) != 34
            or not account_sid.startswith("AC")
        ):
            raise UserError(
                self.env._(
                    "Invalid Twilio Account SID: must start with 'AC' and be 34 characters long."
                )
            )
        if not re.match(r"^[A-Za-z0-9]{32}$", account_sid[2:]):
            raise UserError(
                self.env._(
                    "Invalid Twilio Account SID: must only contain alphanumeric characters after 'AC'."
                )
            )

    def _action_view_sms_twilio_account_manage(self):
        return {
            "name": self.env._("Manage Twilio SMS"),
            "res_model": "sms.twilio.account.manage",
            "res_id": False,
            "context": self.env.context,
            "type": "ir.actions.act_window",
            "views": [(False, "form")],
            "view_mode": "form",
            "target": "new",
        }
