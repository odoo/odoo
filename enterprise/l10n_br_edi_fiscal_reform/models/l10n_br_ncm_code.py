# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10nBrNCMCode(models.Model):
    _inherit = 'l10n_br.ncm.code'

    legal_reference = fields.Char(
        'Legal Reference',
        help='Brazil: Official technical name required for some NCM codes with specific tax rules (e.g. beverages, electronics).'
    )
