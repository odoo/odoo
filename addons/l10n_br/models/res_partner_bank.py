# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models, fields, api, _
from odoo.addons.mail.tools.mail_validation import mail_validate
from odoo.exceptions import ValidationError
from odoo.tools import float_repr


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    proxy_type = fields.Selection(
        selection_add=[
            ("email", "Email Address"),
            ("mobile", "Mobile Number"),
            ("br_cpf_cnpj", "CPF/CNPJ (BR)"),
            ("br_random", "Random Key (BR)"),
        ],
        ondelete={
            "email": "set default",
            "mobile": "set default",
            "br_cpf_cnpj": "set default",
            "br_random": "set default",
        },
    )

    @api.constrains("proxy_type", "proxy_value", "partner_id")
    def _check_br_proxy(self):
        for bank in self.filtered(lambda bank: bank.country_code == "BR" and bank.proxy_type != "none"):
            if bank.proxy_type not in ("email", "mobile", "br_cpf_cnpj", "br_random"):
                raise ValidationError(
                    _(
                        "The proxy type must be Email Address, Mobile Number, CPF/CNPJ (BR) or Random Key (BR) for Pix code generation."
                    )
                )

            value = bank.proxy_value
            if bank.proxy_type == "email" and not mail_validate(value):
                raise ValidationError(_("%s is not a valid email.", value))

            if bank.proxy_type == "br_cpf_cnpj" and (
                not self.partner_id.check_vat_br(value) or any(not char.isdecimal() for char in value)
            ):
                raise ValidationError(_("%s is not a valid CPF or CNPJ (don't include periods or dashes).", value))

            if bank.proxy_type == "mobile" and (not value or not value.startswith("+55") or len(value) != 14):
                raise ValidationError(
                    _(
                        "The mobile number %s is invalid. It must start with +55, contain a 2 digit territory or state code followed by a 9 digit number.",
                        value,
                    )
                )

            regex = r"%(char)s{8}-%(char)s{4}-%(char)s{4}-%(char)s{4}-%(char)s{12}" % {"char": "[a-fA-F0-9]"}
            if bank.proxy_type == "br_random" and not re.fullmatch(regex, bank.proxy_value):
                raise ValidationError(
                    _(
                        "The random key %s is invalid, the format looks like this: 71d6c6e1-64ea-4a11-9560-a10870c40ca2",
                        value,
                    )
                )

    @api.depends("country_code")
    def _compute_display_qr_setting(self):
        """Override."""
        bank_br = self.filtered(lambda b: b.country_code == "BR")
        bank_br.display_qr_setting = True
        super(ResPartnerBank, self - bank_br)._compute_display_qr_setting()

    def _get_additional_data_field(self, comment):
        """Override."""
        if self.country_code == "BR":
            # Only include characters allowed by the Pix spec.
            return self._serialize(5, re.sub(r"[^a-zA-Z0-9*]", "", comment))
        return super()._get_additional_data_field(comment)

    def _get_qr_code_vals_list(self, *args, **kwargs):
        """Override. Force the amount field to always have two decimals. Uppercase the merchant name and merchant city.
        Although not specified explicitly in the spec, not uppercasing causes errors when scanning the code. Also ensure
        there is always some comment set."""
        res = super()._get_qr_code_vals_list(*args, **kwargs)
        if self.country_code == "BR":
            res[5] = (res[5][0], float_repr(res[5][1], 2) if res[5][1] else None)  # amount
            res[7] = (res[7][0], res[7][1].upper())  # merchant_name
            res[8] = (res[8][0], res[8][1].upper())  # merchant_city
            if not res[9][1]:
                res[9] = (res[9][0], self._get_additional_data_field("***"))  # default comment if none is set
        return res

    def _get_merchant_account_info(self):
        """Override."""
        if self.country_code == "BR":
            merchant_account_info_data = (
                (0, "br.gov.bcb.pix"),  # GUI
                (1, self.proxy_value),  # key
            )
            return 26, "".join(self._serialize(*val) for val in merchant_account_info_data)

        return super()._get_merchant_account_info()

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        """Override."""
        if qr_method == "emv_qr" and self.country_code == "BR":
            if currency.name != "BRL":
                return _("Can't generate a Pix QR code with a currency other than BRL.")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(
        self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication
    ):
        """Override."""
        if (
            qr_method == "emv_qr"
            and self.country_code == "BR"
            and self.proxy_type not in ("email", "mobile", "br_cpf_cnpj", "br_random")
        ):
            return _(
                "To generate a Pix code the proxy type for %s must be Email Address, Mobile Number, CPF/CNPJ (BR) or Random Key (BR).",
                self.display_name,
            )

        return super()._check_for_qr_code_errors(
            qr_method, amount, currency, debtor_partner, free_communication, structured_communication
        )
