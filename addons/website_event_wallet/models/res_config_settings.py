# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_add_to_wallet = fields.Boolean(
        related='company_id.allow_add_to_wallet',
        readonly=False,
    )
