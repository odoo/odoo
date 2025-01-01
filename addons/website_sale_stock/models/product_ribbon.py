# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _inherit = 'product.ribbon'

    assign = fields.Selection(
        selection_add=[
            ('out_of_stock', "Out of stock"),
        ],
        ondelete={'out_of_stock': 'cascade'}
    )

    @api.constrains('assign')
    def _check_assign(self):
        super()._check_assign()
        for record in self:
            if record.assign in ['out_of_stock']:
                existing_ribbons = self.search([
                    ('id', '!=', record.id),
                    ('assign', '=', record.assign)
                ], limit=1)
                if existing_ribbons:
                    raise ValidationError(
                        _(
                            "Only one record with the assign %s is allowed." ,
                            dict(self._fields['assign'].selection).get(record.assign)
                        )
                    )

    def _match_assign(self, product, product_prices):
        if self.assign == 'out_of_stock':
            return product._is_sold_out()
        return super()._match_assign(product, product_prices)
