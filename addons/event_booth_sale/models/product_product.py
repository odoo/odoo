# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Product(models.Model):
    _inherit = 'product.product'

    is_event_booth = fields.Boolean(
        compute="_compute_is_event_booth",
        compute_sudo=True,
        search="_search_is_event_booth",
    )

    def _compute_is_event_booth(self):
        has_event_booth_per_product = {
            product.id: bool(count)
            for product, count in self.env['event.booth.category']._read_group(
                domain=[('product_id', 'in', self.ids)],
                groupby=['product_id'],
                aggregates=['__count'],
            )
        }
        for product in self:
            product.is_event_booth = has_event_booth_per_product.get(product.id, False)

    def _search_is_event_booth(self, operator, value):
        EventBoothCategory = self.env['event.booth.category']
        subquery = EventBoothCategory.sudo()._search([])
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'inselect'
        else:
            search_operator = 'not inselect'

        return [
            ('id', search_operator, subquery.select('"%s"."product_id"' % EventBoothCategory._table)
        )]
