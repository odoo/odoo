# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_cpa005_short_name = fields.Char(
        "Short Name used in Canadian EFT",
        size=15,
        help="15 character field used to represent a short version of the Originator's name in Canadian EFT files. It will "
        "typically be used for bank statements. Most banks require this value to be all uppercase.",
    )
