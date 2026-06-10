# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    website_id = fields.Many2one(
        comodel_name="website",
        help="Website through which this invoice was created for eCommerce orders.",
        readonly=True,
    )

    def preview_invoice(self):
        action = super().preview_invoice()
        # Only preview the invoice inside the website editor when its company
        # actually has a website. Otherwise fall back to the plain portal page,
        # exactly as if the website module were not installed.
        if self._get_portal_website() and action["url"].startswith("/"):
            # URL should always be relative, safety check
            action["url"] = f"/@{action['url']}"
        return action
