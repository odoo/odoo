# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class UoM(models.Model):
    _inherit = "uom.uom"

    # As per FBR Rules you need to Specify UQC given by FBR.
    l10n_pk_code = fields.Char("Pakistan UQC", help="Unique Quantity Code (UQC)")
