# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_us_adp_code = fields.Char(
        related='company_id.l10n_us_adp_code',
        readonly=False)
