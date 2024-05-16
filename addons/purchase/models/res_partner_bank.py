# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dataclasses import dataclass

from odoo import api, fields, models, _


@dataclass
class FrontendFieldSpec:
    """Used to specify res.partner.bank fields in the frontend. Different countries require different forms, e.g. in
    the US you want a W9 or equivalent before paying a vendor.

    Attributes:
    - country_id: whether this field is country-specific and thus should only be shown when creating bank accounts in
                  this country.
    - type: "text" or "file", "text" fields will be stored the res.partner.bank field with the same name. "file" fields
            are meant for PDFs and stored as an attachment.
    - name: technical name of the field, for "text" type fields this should be a field on res.partner.bank.
    - label: displayed to users on the website during bank account creation.
    - required: whether to require the field on the website.
    - placeholder: mainly useful for tests in case a particular field has some special constraints for which dummy data
                   can't easily be generated.
    """

    country_id: int | None
    type: str
    name: str
    label: str
    required: bool
    placeholder: str = None


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    masked_acc_number = fields.Char(
        "Masked Account Number",
        compute="_compute_portal_display_fields",
        help="The last 4 digits of the account number, prefixed by ****. When displaying the full account number is not strictly needed, this is a more secure option.",
    )
    portal_display_name = fields.Char(
        "Portal Display Name",
        compute="_compute_portal_display_fields",
        help="The bank name together with the masked account number.",
    )

    @api.depends("bank_id.name", "acc_number")
    def _compute_portal_display_fields(self):
        for partner_bank in self:
            masked = "****" + partner_bank.acc_number[-4:]
            partner_bank.masked_acc_number = masked
            partner_bank.portal_display_name = " - ".join([partner_bank.bank_id.name or "", masked])

    @api.model
    def _get_frontend_bank_account_fields(self):
        """Return a list of all the res.partner.bank fields to be used during bank account creation.

        :returns: list of FrontFieldSpec dataclass objects.
        """
        return [
            FrontendFieldSpec(
                country_id=None, type="text", name="acc_number", label=_("Account number"), required=True
            ),
            FrontendFieldSpec(
                country_id=None, type="text", name="acc_holder_name", label=_("Account holder name"), required=True
            ),
            FrontendFieldSpec(
                country_id=None, type="file", name="certificate", label=_("Bank certificate"), required=True
            ),
        ]

    @api.model
    def _get_frontend_bank_account_fields_for_country(self, country_code):
        country_id = self.env["res.country"].search([("code", "=", country_code)], limit=1).id
        return [
            field
            for field in self._get_frontend_bank_account_fields()
            if field.country_id is None or field.country_id == country_id
        ]

    @api.model
    def _get_required_frontend_bank_account_fields(self, country_code):
        return [
            field.name for field in self._get_frontend_bank_account_fields_for_country(country_code) if field.required
        ]

    @api.model
    def _get_regular_frontend_bank_account_fields(self, country_code):
        return [
            field.name
            for field in self._get_frontend_bank_account_fields_for_country(country_code)
            if field.type != "file"
        ]

    @api.model
    def _get_attachment_frontend_bank_account_fields(self, country_code):
        return [
            field.name
            for field in self._get_frontend_bank_account_fields_for_country(country_code)
            if field.type == "file"
        ]
