# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    allow_add_to_wallet = fields.Boolean(
        related='company_id.allow_add_to_wallet', readonly=True,
    )
    has_wallet_provider = fields.Boolean(
        string="Has Available Wallet", compute='_compute_has_wallet_provider',
    )
    wallet_background_image = fields.Image(
        string="Wallet Background", max_width=2048, max_height=2048,
        help="Background used for digital wallet passes. If empty, the company's colors are used.",
    )

    @api.depends('company_id', 'company_id.allow_add_to_wallet')
    def _compute_has_wallet_provider(self):
        for event in self:
            # Event editors only need availability, never signing material.
            event.has_wallet_provider = bool(event.company_id.sudo()._get_available_wallet_providers())
