# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    allow_add_to_wallet = fields.Boolean(
        string="Allow Adding to Wallet",
        help="Allow attendees to add this event's ticket to their mobile wallet.",
    )

    def _get_available_wallet_providers(self, **kwargs):
        """Return registered provider codes with a usable company certificate."""
        self.ensure_one()
        if not self.allow_add_to_wallet:
            return []
        Certificate = self.env['certificate.certificate']
        return [
            code for code in Certificate._get_wallet_provider_scopes(**kwargs)
            if Certificate._get_wallet_certificate(self, code, **kwargs)
        ]
