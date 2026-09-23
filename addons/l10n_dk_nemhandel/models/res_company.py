from urllib.parse import urljoin

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.account.models.res_company import PEPPOL_LIST

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "nemhandel_identifier_type",
        "nemhandel_identifier_value",
    )

    l10n_dk_nemhandel_config_id = fields.Many2one(
        comodel_name="l10n_dk_nemhandel.config",
        compute="_compute_l10n_dk_nemhandel_config_id",
        search="_search_l10n_dk_nemhandel_config_id",
    )

    def _search_l10n_dk_nemhandel_config_id(self, operator, value):
        return self._search_config_link("l10n_dk_nemhandel.config", operator, value)

    def _compute_l10n_dk_nemhandel_config_id(self):
        configs = self.env["l10n_dk_nemhandel.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_dk_nemhandel_config_id = by_company.get(company.id, False)

    @api.model
    def _check_phonenumbers_import(self):
        if not phonenumbers:
            raise ValidationError(
                self.env._("Please install the phonenumbers library.")
            )

    def _normalize_nemhandel_phone_number(self, phone_number=None):
        self.check_singleton()

        error_message = self.env._(
            "Please enter the phone number in the correct international format.\n"
            "For example: +32123456789, where +32 is the country code.\n"
            "Currently, only European countries are supported."
        )

        self._check_phonenumbers_import()

        phone_number = (
            phone_number or self.l10n_dk_nemhandel_config_id.nemhandel_phone_number
        )
        if not phone_number:
            return

        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"

        try:
            phone_nbr = phonenumbers.parse(phone_number)
        except phonenumbers.phonenumberutil.NumberParseException as e:
            raise ValidationError(error_message) from e

        country_code = phonenumbers.phonenumberutil.region_code_for_number(phone_nbr)
        if country_code not in PEPPOL_LIST or not phonenumbers.is_valid_number(
            phone_nbr
        ):
            raise ValidationError(error_message)

    def _get_nemhandel_edi_mode(self):
        self.check_singleton()
        config_param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_dk_nemhandel.edi.mode")
        )
        return (
            self.sudo().l10n_dk_nemhandel_config_id.nemhandel_edi_user.edi_mode
            or config_param
            or "prod"
        )

    def _get_nemhandel_webhook_endpoint(self):
        self.check_singleton()
        return urljoin(self.get_base_url(), "/nemhandel/webhook")
