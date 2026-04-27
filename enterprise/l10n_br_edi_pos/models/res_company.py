# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_edi_csc_identifier = fields.Char(
        "CSC ID",
        size=5,
        help="Brazil: the CSC ID or CSC Token is an identification of the Taxpayer Security Code, which can have 1 to 6 digits and is available on the website of the State Department of Finance (SEFAZ) of your state.",
    )
    l10n_br_edi_csc_number = fields.Char(
        "CSC Number",
        help="Brazil: the CSC Number is a code of up to 36 characters that only you and the Department of Finance know. It is used to generate the QR Code of the NFC-e and ensure the authenticity of the DANFE.",
    )
    l10n_br_edi_url_key_override = fields.Char(
        "URL Key Override",
        help="Brazil: this is the website shown to the user for her to access the NFC-e online. If not set we will send the default for your state.",
    )
    l10n_br_edi_qr_url_override = fields.Char(
        "QR URL Override",
        help="Brazil: this is the URL used on the QR code for scanning. If not set we will send the default for your state.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.account_fiscal_country_id.code == "BR":
            params += ["l10n_br_avalara_environment"]
        return params
