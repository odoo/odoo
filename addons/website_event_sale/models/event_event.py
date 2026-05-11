# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _build_event_offer_jsonld(self, ticket):
        """
        Add ticket pricing to the structured data offer.
        """
        offer_jsonld = super()._build_event_offer_jsonld(ticket)
        website = self.env['website'].get_current_website()
        if website.show_line_subtotals_tax_selection == 'tax_excluded':
            price = ticket.total_price_reduce
        else:
            price = ticket.total_price_reduce_taxinc
        offer_jsonld.set({
            'price': price,
            'priceCurrency': self.company_id.currency_id.name,
        })
        return offer_jsonld
