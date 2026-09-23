import contextlib
import re

import requests
from lxml import etree
from stdnum import ean, get_cc_module

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.account.models.res_company import PEPPOL_LIST

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


def _cc_checker(country_code, code_type):
    return lambda endpoint: get_cc_module(country_code, code_type).is_valid(endpoint)


def _re_sanitizer(expression):
    return lambda endpoint: (
        res.group(0) if (res := re.search(expression, endpoint)) else endpoint
    )


PEPPOL_ENDPOINT_RULES = {
    "0007": _cc_checker("se", "orgnr"),
    "0088": ean.is_valid,
    "0184": _cc_checker("dk", "cvr"),
    "0192": _cc_checker("no", "orgnr"),
    "0208": _cc_checker("be", "vat"),
}
PEPPOL_ENDPOINT_WARNINGS = {
    "0151": _cc_checker("au", "abn"),
    "0201": lambda endpoint: bool(re.match(r"[0-9a-zA-Z]{6}$", endpoint)),
    "0210": _cc_checker("it", "codicefiscale"),
    "0211": _cc_checker("it", "iva"),
    "9906": _cc_checker("it", "iva"),
    "9907": _cc_checker("it", "codicefiscale"),
}
PEPPOL_ENDPOINT_SANITIZERS = {
    "0007": _re_sanitizer(r"\d{10}"),
    "0184": _re_sanitizer(r"\d{8}"),
    "0192": _re_sanitizer(r"\d{9}"),
    "0208": _re_sanitizer(r"\d{10}"),
}
TIMEOUT = 10


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "peppol_eas",
        "peppol_endpoint",
    )
    _CREDENTIAL_FIELDS = {
        "account_peppol_migration_key": "account_peppol_migration_key",
    }

    account_peppol_migration_key = fields.Char(
        string="Migration Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )

    account_peppol_config_id = fields.Many2one(
        comodel_name="account_peppol.config",
        compute="_compute_account_peppol_config_id",
        search="_search_account_peppol_config_id",
    )

    def _search_account_peppol_config_id(self, operator, value):
        return self._search_config_link("account_peppol.config", operator, value)

    def _compute_account_peppol_config_id(self):
        configs = self.env["account_peppol.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.account_peppol_config_id = by_company.get(company.id, False)

    def _get_active_peppol_parent_company(self):
        """
        Gets the closest parent company (relative from the current)
        that has an active peppol connection.
        :return: res.company record: containing single company if found, empty if not.
        """
        self.check_singleton()

        for parent_company in self.sudo().parent_ids[::-1][
            1:
        ]:  # loop through parent companies starting from the closest parent
            if parent_company.sudo().account_peppol_config_id.peppol_can_send:
                return parent_company

        return self.env["res.company"]

    def _have_unauthorized_peppol_parent_company(self):
        """
        Returns True if the company is using the active peppol connection of the parent company
        but the user does not have access to that parent company.
        """
        self.check_singleton()
        parent_company = self.account_peppol_config_id.peppol_parent_company_id
        return parent_company and parent_company not in self.env.user.company_ids

    def _reset_peppol_configuration(self, soft=False):
        """
        Reset all peppol configuration fields to their default value before registering.
        The EAS, endpoint, email, and phone number will be recomputed so that branch companies that uses
        their parent configuration can have their default values back
        (as these fields will be overwritten for them when they register as parent).

        :param soft: If True, will only set state to unregistered, but keep peppol config intact, so the user can register again
        """
        self.account_peppol_config_id.account_peppol_proxy_state = "not_registered"
        self.account_peppol_migration_key = False
        if not soft:
            self.account_peppol_config_id.peppol_external_provider = False
            self.peppol_eas = False
            self.peppol_endpoint = False
            self.account_peppol_config_id.account_peppol_contact_email = False
            self.account_peppol_config_id.account_peppol_phone_number = False

            self.account_peppol_config_id._compute_account_peppol_contact_email()
            self.account_peppol_config_id._compute_account_peppol_phone_number()
        self.partner_id._compute_peppol_eas()
        self.partner_id._compute_peppol_endpoint()

    @api.model
    def _check_phonenumbers_import(self):
        if not phonenumbers:
            raise ValidationError(
                self.env._("Please install the phonenumbers library.")
            )

    def _normalize_peppol_phone_number(self, phone_number=None):
        self.check_singleton()

        error_message = self.env._(
            "Please enter the mobile number in the correct international format.\n"
            "For example: +32123456789, where +32 is the country code.\n"
            "Currently, only European countries are supported."
        )

        self._check_phonenumbers_import()

        phone_number = (
            phone_number or self.account_peppol_config_id.account_peppol_phone_number
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

    def _check_peppol_endpoint_number(self, warning=False):
        self.check_singleton()
        peppol_dict = PEPPOL_ENDPOINT_WARNINGS if warning else PEPPOL_ENDPOINT_RULES

        return (
            True
            if (endpoint_rule := peppol_dict.get(self.peppol_eas)) is None
            else endpoint_rule(self.peppol_endpoint)
        )

    @api.constrains("peppol_endpoint")
    def _check_peppol_endpoint(self):
        for company in self:
            if not company.peppol_endpoint:
                continue
            if not company._check_peppol_endpoint_number(PEPPOL_ENDPOINT_RULES):
                raise ValidationError(
                    self.env._(
                        "The Peppol endpoint identification number is not correct."
                    )
                )

    def _first_journal_per_company(self, journal_type):
        journals = self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(self),
                ("type", "=", journal_type),
            ]
        )
        return {
            company: next(
                (
                    journal
                    for journal in journals
                    if not journal.company_id or journal.company_id == company
                ),
                self.env["account.journal"],
            )
            for company in self
        }

    @api.model
    def _update_peppol_endpoint_in_values(self, values):
        eas = values.get("peppol_eas")
        endpoint = values.get("peppol_endpoint")
        if not eas or not endpoint:
            return
        if sanitizer := PEPPOL_ENDPOINT_SANITIZERS.get(eas):
            new_endpoint = sanitizer(endpoint)
            if new_endpoint:
                values["peppol_endpoint"] = new_endpoint

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._update_peppol_endpoint_in_values(vals)

        res = super().create(vals_list)
        if res:
            for company in res:
                self.env["ir.default"].sudo().set(
                    "res.partner",
                    "peppol_verification_state",
                    "not_verified",
                    company_id=company.id,
                )
        return res

    def write(self, vals):
        self._update_peppol_endpoint_in_values(vals)
        return super().write(vals)

    def _peppol_modules_document_types(self):
        """Override this function to add supported document types as modules are installed.

        :returns: dictionary of the form: {module_name: [(document identifier, document_name)]}
        """
        return {
            "default": {
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1": "Peppol BIS Billing UBL Invoice V3",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1": "Peppol BIS Billing UBL CreditNote V3",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1": "Peppol BIS Self-Billing UBL Invoice V3",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1": "Peppol BIS Self-Billing UBL CreditNote V3",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0::2.1": "SI-UBL 2.0 Invoice",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0::2.1": "SI-UBL 2.0 CreditNote",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0::2.1": "XRechnung UBL Invoice V2.0",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0::2.1": "XRechnung UBL CreditNote V2.0",
            }
        }

    def _peppol_supported_document_types(self):
        """Returns a flattened dictionary of all supported document types."""
        return {
            identifier: document_name
            for identifiers in self._peppol_modules_document_types().values()
            for identifier, document_name in identifiers.items()
        }

    def _get_peppol_edi_mode(self, temporary_eas=False):
        self.check_singleton()
        config_param = (
            self.env["ir.config_parameter"].sudo().get_param("account_peppol.edi.mode")
        )
        # by design, we can only have zero or one proxy user per company with type Peppol
        peppol_user = self.sudo().account_edi_proxy_client_ids.filtered(
            lambda u: u.proxy_type == "peppol"
        )
        demo_if_demo_identifier = (
            "demo" if (temporary_eas or self.peppol_eas) == "odemo" else False
        )
        return demo_if_demo_identifier or peppol_user.edi_mode or config_param or "prod"

    def _get_peppol_webhook_endpoint(self):
        self.check_singleton()
        return urljoin(self.get_base_url(), "/peppol/webhook")

    def _get_company_info_on_peppol(self, edi_identification):

        def _get_peppol_provider(participant_info):
            if not participant_info:
                return None
            services = participant_info.get("services", [])
            if not services:
                return None

            service_href = services[0].get("href")

            provider_name = None
            with contextlib.suppress(
                requests.exceptions.RequestException, etree.XMLSyntaxError
            ):
                response = self.env["ir.egress"].request(
                    "GET", service_href, purpose="peppol_smp", timeout=TIMEOUT
                )
                if response.status_code == 200:
                    access_point_info = etree.fromstring(response.content)
                    provider_name = access_point_info.findtext(
                        ".//{*}ServiceDescription"
                    )
            return provider_name

        self.check_singleton()
        is_company_on_peppol = False
        external_provider = None
        error_msg = ""
        if (
            participant_info := self.partner_id._peppol_get_participant(
                edi_identification
            )
        ) is not None and (
            is_company_on_peppol := self.partner_id._check_peppol_participant_exists(
                participant_info, edi_identification
            )
        ):
            error_msg = self.env._(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to a Peppol service, please deregister."
            )
            if (
                external_provider := _get_peppol_provider(participant_info)
            ) and "Odoo" not in external_provider:
                error_msg += self.env._(
                    "The Peppol service that is used is %s.", external_provider
                )
        return {
            "is_on_peppol": is_company_on_peppol,
            "external_provider": external_provider,
            "error_msg": error_msg,
        }

    def _account_peppol_send_welcome_email(self):
        self.check_singleton()
        if self.account_peppol_config_id.account_peppol_proxy_state not in (
            "sender",
            "receiver",
        ):
            return

        mail_template = self.env.ref(
            "account_peppol.mail_template_peppol_registration", raise_if_not_found=False
        )
        if not mail_template:
            return

        mail_template.send_mail(self.id, force_send=True)
