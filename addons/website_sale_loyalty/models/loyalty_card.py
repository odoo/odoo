# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class LoyaltyCard(models.Model):
    _inherit = "loyalty.card"

    def action_coupon_share(self):
        self.ensure_one()
        return self.env["coupon.share"].create_share_action(coupon=self)

    def _is_usable_for_payment(self):
        """Override of `loyalty` to only pay on a website with cards available on it."""
        if not super()._is_usable_for_payment():
            return False
        website = self.env.website
        program = self.program_id
        return not website or (
            program.ecommerce_ok and (not program.website_id or program.website_id == website)
        )
