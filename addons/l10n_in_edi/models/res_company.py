from datetime import UTC

from stdnum.in_ import gstin, pan

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.libs.datetime import timezone


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_in_edi_password": "l10n_in_edi_password",
        "l10n_in_edi_token": "l10n_in_edi_token",
    }

    # E-Invoice fields
    l10n_in_edi_feature = fields.Boolean(string="Indian E-Invoicing")
    l10n_in_edi_username = fields.Char(
        string="E-invoice (IN) Username",
        groups="base.group_system",
    )
    l10n_in_edi_password = fields.Char(
        string="E-invoice (IN) Password",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
    l10n_in_edi_token = fields.Char(
        string="E-invoice (IN) Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
    l10n_in_edi_token_validity = fields.Datetime(
        string="E-invoice (IN) Valid Until",
        groups="base.group_system",
    )

    # E-Invoice Business Methods

    def _l10n_in_edi_token_is_valid(self):
        self.check_singleton()
        return (
            self.l10n_in_edi_token
            and self.l10n_in_edi_token_validity > fields.Datetime.now()
        )

    def _l10n_in_edi_get_token(self):
        self_sudo = self.sudo()
        if self_sudo.l10n_in_edi_username and self_sudo._l10n_in_edi_token_is_valid():
            return self_sudo.l10n_in_edi_token
        elif self_sudo.l10n_in_edi_username and self_sudo.l10n_in_edi_password:
            self_sudo._l10n_in_edi_authenticate()
            return self_sudo.l10n_in_edi_token
        return False

    def _l10n_in_edi_authenticate(self):
        self_sudo = self.sudo()
        params = {
            "username": self_sudo.l10n_in_edi_username,
            "password": self_sudo.l10n_in_edi_password,
            "gstin": self_sudo.vat,
        }
        try:
            response = self.env["iap.account"]._l10n_in_connect_to_server(
                self_sudo.l10n_in_edi_production_env,
                params,
                "/iap/l10n_in_edi/1/authenticate",
                "l10n_in_edi.endpoint",
            )
        except AccessError:
            return {
                "error": [
                    {
                        "code": "404",
                        "message": _(
                            "Unable to connect to the online E-invoice service. "
                            "The web service may be temporary down. Please try again in a moment."
                        ),
                    }
                ]
            }
        # validity data-time in Indian standard time(UTC+05:30) convert IST to UTC
        if data := response.get("data"):
            tz = timezone("Asia/Kolkata")
            local_time = fields.Datetime.to_datetime(data["TokenExpiry"]).replace(
                tzinfo=tz
            )
            utc_time = local_time.astimezone(UTC)
            self_sudo.write(
                {
                    "l10n_in_edi_token_validity": fields.Datetime.to_string(utc_time),
                    "l10n_in_edi_token": data["AuthToken"],
                }
            )
        return response

    def _l10n_in_check_einvoice_validation(self):
        checks = {
            "company_address_missing": {
                "fields": (
                    "street",
                    "zip",
                    "city",
                    "state_id",
                    "country_id",
                ),
                "message": _(
                    "Companies should have a complete address, verify their Street, City, State, Country and Zip code."
                ),
            },
        }
        return {
            f"l10n_in_edi_{key}": {
                "message": check["message"],
                "action_text": (
                    _("View Companies")
                    if len(invalid_records) > 1
                    else _("View %s", invalid_records.name)
                ),
                "action": invalid_records._get_records_action(
                    name=_("Check Company Data")
                ),
            }
            for key, check in checks.items()
            if (
                invalid_records := self.filtered(
                    lambda record: any(not record[field] for field in check["fields"])
                )
            )
        }
