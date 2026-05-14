# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _build_offer_jsonld_vals(self, ticket):
        offer = super()._build_offer_jsonld_vals(ticket)
        website = self.env["website"].get_current_website()
        if website.show_line_subtotals_tax_selection == "tax_excluded":
            price = ticket.total_price_reduce
        else:
            price = ticket.total_price_reduce_taxinc
        # total_price_reduce is in the ticket currency; convert it to the
        # website currency to match the price shown on the page.
        price = ticket.currency_id._convert(price, website.currency_id, self.company_id)
        offer.update({
            "price": price,
            "priceCurrency": website.currency_id.name,
        })
        return offer
