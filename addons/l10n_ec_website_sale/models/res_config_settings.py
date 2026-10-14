# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ec_final_consumer_limit = fields.Float(
        related='website_id.l10n_ec_final_consumer_limit',
        readonly=False,
    )
