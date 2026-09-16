# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventBoothCategory(models.Model):
    _inherit = 'event.booth.category'

    def _prepare_jsonld_vals(self):
        vals = super()._prepare_jsonld_vals()
        category_sudo = self.sudo()
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        event_sudo = self.env['event.event'].browse(self.env.context.get('event_id')).sudo()
        price = (
            category_sudo.price_reduce_taxinc
            if website.show_line_subtotals_tax_selection == 'tax_included'
            else category_sudo.price_reduce
        )
        vals['offers'] = {
            '@type': 'Offer',
            'price': event_sudo.company_id.currency_id._convert(
                price, website.currency_id, event_sudo.company_id,
            ),
            'priceCurrency': website.currency_id.name,
            'availability': (
                'https://schema.org/InStock'
                if self in event_sudo.event_booth_category_available_ids
                else 'https://schema.org/SoldOut'
            ),
        }
        return vals
