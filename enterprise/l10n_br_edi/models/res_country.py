# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCountry(models.Model):
    _inherit = "res.country"

    l10n_br_edi_code = fields.Char(
        "BR Country Code", help="Brazil: Country Code used in NF-e", readonly=True
    )
