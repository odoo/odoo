# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AmazonOffer(models.Model):
    _inherit = "amazon.offer"

    amazon_channel = fields.Selection(
        string="Fulfillment Channel",
        help="The channel will be updated with the incoming orders or during the next stock"
        " synchronization.",
        selection=[("fbm", "Fulfilled by Merchant"), ("fba", "Fulfilled by Amazon")],
        compute="_compute_amazon_channel",
        inverse="_inverse_amazon_channel",
    )

    @api.depends("amazon_feed_ref")
    def _compute_amazon_channel(self):
        """Compute the Amazon channel based on the JSON-formatted feed data that might be stored in
        the `amazon_feed_ref` field.

        If the `amazon_feed_ref` holds a plain, non-JSON string, the Amazon channel cannot be
        determined.
        """
        feed_data_by_offer = self.with_context(amzn_fetch_missing_data=False)._get_feed_data()
        for offer in self:
            match feed_data_by_offer.get(offer, {}).get("is_fbm"):
                case True:
                    offer.amazon_channel = "fbm"
                case False:
                    offer.amazon_channel = "fba"
                case None:
                    offer.amazon_channel = None

    def _inverse_amazon_channel(self):
        feed_data_by_offer = self.with_context(amzn_fetch_missing_data=False)._get_feed_data()
        for offer in self.filtered("amazon_channel"):
            feed_data = feed_data_by_offer.setdefault(offer, {})
            if not offer.amazon_channel:
                feed_data.pop("is_fbm", None)
            else:
                feed_data["is_fbm"] = offer.amazon_channel == "fbm"
        self._save_feed_data(feed_data_by_offer)
