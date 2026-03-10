# Copyright (C) 2022-Today - Engenere (<https://engenere.one>).
# @author Antônio S. Pereira Neto <neto@engenere.one>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import phonenumbers
from email_validator import EmailSyntaxError, validate_email

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools import check_cnpj_cpf


class PartnerPix(models.Model):
    _name = "res.partner.pix"
    _description = "Brazilian instant payment ecosystem (Pix)"
    _order = "sequence, id"
    _rec_name = "key"

    _sql_constraints = [
        (
            "partner_pix_key_unique",
            "unique(key_type, key, partner_id)",
            "A Pix Key with this values already exists in this partner.",
        )
    ]

    KEY_TYPES = [
        ("cnpj_cpf", _("CPF or CNPJ")),
        ("phone", _("Phone Number")),
        ("email", _("E-mail")),
        ("evp", _("Random Key")),
    ]

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        ondelete="cascade",
        required=True,
    )
    sequence = fields.Integer(default=10)
    key_type = fields.Selection(
        selection=KEY_TYPES,
        string="Type",
        required=True,
    )
    key = fields.Char(
        help="PIX Addressing key",
        required=True,
    )

    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Bank Account",
        domain="[('partner_id', '=', partner_id)]",
    )

    @api.model
    def _normalize_email(self, email):
        try:
            result = validate_email(
                email,
                check_deliverability=False,
            )
        except EmailSyntaxError as e:
            raise ValidationError(_(f"{email.strip()} is an invalid email")) from e
        normalized_email = result.local_part + "@" + result.domain
        if len(normalized_email) > 77:
            raise ValidationError(
                _(
                    f"The email is too long, "
                    f"a maximum of 77 characters is allowed: \n{email.strip()}"
                )
            ) from None
        return normalized_email

    @api.model
    def _normalize_phone(self, phone):
        try:
            phonenumber = phonenumbers.parse(phone, "BR")
        except phonenumbers.phonenumberutil.NumberParseException as e:
            raise ValidationError(_(f"Unable to parse {phone}: {str(e)}")) from e
        if not phonenumbers.is_possible_number(phonenumber):
            raise ValidationError(
                _(f"Impossible number {phone}: probably invalid number of digits.")
            ) from None
        if not phonenumbers.is_valid_number(phonenumber):
            raise ValidationError(
                _(f"Invalid number {phone}: probably incorrect prefix.")
            ) from None
        phone = phonenumbers.format_number(
            phonenumber, phonenumbers.PhoneNumberFormat.E164
        )
        return phone

    @api.model
    def _normalize_cnpj_cpf(self, doc_number, partner_id):
        doc_number = "".join(char for char in doc_number if char.isdigit())
        partner = self.env["res.partner"].browse(partner_id)
        check_cnpj_cpf(self.env, doc_number, partner.country_id)

        return doc_number

    @api.model
    def _normalize_evp(self, key):
        # EVP: Endereço Virtual de Pagamento (chave aleatória)
        # ex: 123e4567-e12b-12d1-a456-426655440000
        key = "".join(key.split())
        if len(key) != 36:
            raise ValidationError(
                _(f"Invalid Random Key: {key}, cannot be longer than 35 characters")
            )
        blocks = key.split("-")
        if len(blocks) != 5:
            raise ValidationError(
                _(f"Invalid Random Key: {key}, the key must consist of five blocks.")
            )
        for block in blocks:
            try:
                int(block, 16)
            except ValueError as e:
                raise ValidationError(
                    _(
                        f"Invalid Random Key: {key} \nthe block {block} "
                        f"is not a valid hexadecimal format."
                    )
                ) from e
        return key

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self.check_vals(vals)
        return super().write(vals)

    @api.model
    def check_vals(self, vals):
        key_type = vals.get("key_type") or self.key_type
        key = vals.get("key") or self.key
        if not key or not key_type:
            return
        if key_type == "email":
            key = self._normalize_email(key)
        elif key_type == "phone":
            key = self._normalize_phone(key)
        elif key_type == "cnpj_cpf":
            partner_id = vals.get("partner_id") or self.partner_id.id
            key = self._normalize_cnpj_cpf(key, partner_id)
        elif key_type == "evp":
            key = self._normalize_evp(key)
        vals["key"] = key
