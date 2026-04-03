# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _to_structured_data_ticket_offer(self, ticket, event_url, now):
        """Add ticket pricing to the structured data offer.

        Uses the tax-included or tax-excluded price depending on the
        website's ``show_line_subtotals_tax_selection`` setting, matching
        the price displayed on the event page.
        """
        offer = super()._to_structured_data_ticket_offer(ticket, event_url, now)
        if not offer:
            return offer

        website = self.env['website'].get_current_website()
        if website.show_line_subtotals_tax_selection == 'tax_excluded':
            price = ticket.total_price_reduce
        else:
            price = ticket.total_price_reduce_taxinc

        currency = self.company_id.currency_id.name
        offer.set(price=price, price_currency=currency)
        return offer
