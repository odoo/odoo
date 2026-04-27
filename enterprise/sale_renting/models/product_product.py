# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_in_rent = fields.Float("Quantity currently in rent", compute='_get_qty_in_rent')

    @api.depends('rent_ok')
    @api.depends_context('rental_products')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self._context.get('rental_products'):
            return
        for product in self:
            if product.rent_ok:
                product.display_name = _("%s (Rental)", product.display_name)

    def _get_qty_in_rent_domain(self):
        return [
            ('is_rental', '=', True),
            ('product_id', 'in', self.ids),
            ('state', '=', 'sale')]

    def _get_qty_in_rent(self):
        """
        Note: we don't use product.with_context(location=self.env.company.rental_loc_id.id).qty_available
        because there are no stock moves for services (which can be rented).
        """
        active_rental_lines = self.env['sale.order.line']._read_group(
            domain=self._get_qty_in_rent_domain(),
            groupby=['product_id'],
            aggregates=['qty_delivered:sum', 'qty_returned:sum'],
        )
        res = {product.id: qty_delivered - qty_returned for product, qty_delivered, qty_returned in active_rental_lines}
        for product in self:
            product.qty_in_rent = res.get(product.id, 0)

    def _compute_delay_price(self, duration):
        """Compute daily and hourly delay price.

        :param timedelta duration: datetime representing the delay.
        """
        days = duration.days
        hours = duration.seconds // 3600
        return days * self.extra_daily + hours * self.extra_hourly

    def _get_best_pricing_rule(self, **kwargs):
        """Return the best pricing rule for the given duration.

        :return: least expensive pricing rule for given duration
        :rtype: product.pricing
        """
        return self.product_tmpl_id._get_best_pricing_rule(product=self, **kwargs)

    def action_view_rentals(self):
        """Access Gantt view of rentals (sale.rental.schedule), filtered on variants of the current template."""
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.rental.schedule",
            "name": _("Scheduled Rentals"),
            "views": [[False, "gantt"]],
            'domain': [('product_id', 'in', self.ids)],
            'context': {
                'search_default_Rentals':1,
                'group_by':[],
                'restrict_renting_products': True,
            }
        }
