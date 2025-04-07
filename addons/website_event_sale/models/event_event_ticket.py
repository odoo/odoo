# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import microdata as md


class EventEventTicket(models.Model):
    _inherit = 'event.event.ticket'

    def _to_markup_data(self) -> md.Offer:
        self.ensure_one()
        availability = (
            md.ItemAvailability.InStock if self.seats_available > 0
            else md.ItemAvailability.SoldOut
        )
        retval = md.Offer(
            name=self.name or None,
            availability=availability,
            category=md.OfferCategory.Paid if self.price_reduce_taxinc != 0.0 else md.OfferCategory.Free,
            price=self.price_reduce_taxinc,
            price_currency=self.event_id.currency_id.name,
            valid_from=self.start_sale_datetime or None,
            valid_through=self.end_sale_datetime or None,
            url=self.event_id.event_register_url
        )
        return retval
