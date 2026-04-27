from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    l10n_pe_code = fields.Char("Code PE", help="Country code to be used on purchase reports.")
    l10n_pe_agreement_code = fields.Char(
        "Agreement Code", help="Agreement code defined by SUNAT to avoid double taxation."
    )
