# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import _, api, models
from odoo.osv import expression
from odoo.tools import float_is_zero


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for product in self:
            if product.rent_ok and not product.sale_ok:
                product.show_forecasted_qty_status_button = False

    @api.depends('type', 'rent_ok', 'qty_available', 'qty_in_rent')
    @api.depends_context('sale_stock_renting_show_total_qty', 'allowed_company_ids')
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('sale_stock_renting_show_total_qty'):
            storable_rental_products = self.filtered(
                lambda product: product.rent_ok and product.is_storable
            )
            if not storable_rental_products:
                return

            # Rental/Stock qties only have to be computed on the current date to know the current
            # total qty (in stock + in rental)
            ctxt = {
                'from_date': self.env.cr.now(),
                'to_date': self.env.cr.now(),
            }

            # Generate new display_name results
            for product in storable_rental_products.with_context(**ctxt):
                total_qty = product.qty_available + product.qty_in_rent
                if int(total_qty) == total_qty:
                    # Display as integer if float has no decimal value
                    total_qty = int(total_qty)
                if total_qty in (0, 1):
                    product.display_name = _(
                        "%(product)s (%(qty)s item)",
                        product=product.display_name,
                        qty=total_qty,
                    )
                else:
                    product.display_name = _(
                        "%(product)s (%(qty)s items)",
                        product=product.display_name,
                        qty=total_qty,
                    )

    def _get_domain_locations_new(self, location_ids):
        domain_quant, domain_move_in_loc, domain_move_out_loc = super()._get_domain_locations_new(location_ids)
        if self.env.context.get('ignore_rental_returns'):
            rental_loc_ids = self.env.companies.rental_loc_id.ids
            domain_move_in_loc = expression.AND([domain_move_in_loc, [('location_id', 'not in', rental_loc_ids)]])
        return domain_quant, domain_move_in_loc, domain_move_out_loc

    def _get_qty_in_rent_domain(self):
        """Allow precising the warehouse_id to get qty currently in rent."""
        warehouse_id = self.env['stock.warehouse']._get_warehouse_id_from_context()
        if warehouse_id:
            return super()._get_qty_in_rent_domain() + [
                ('order_id.warehouse_id', '=', warehouse_id)
            ]
        else:
            return super()._get_qty_in_rent_domain()

    def _get_unavailable_qty(self, from_date, to_date=None, **kwargs):
        """ Return the max quantity of self (unique) unavailable between from_date and to_date.

        Early pickups and returns are taken into account.
        :param datetime from_date:
        :param datetime to_date:
        :param dict kwargs: search domain restrictions (ignored_soline_id, warehouse_id)
        """
        # If to_date isn't provided, the interval should be a single instant (i.e. from_date).
        to_date = to_date or from_date
        rented_quantities, key_dates = self._get_active_rental_lines(
            from_date, to_date, **kwargs
        )._get_rented_quantities([from_date, to_date])

        unavailable_quantity = 0
        max_unavailable_qty = 0
        for key_date in key_dates:
            if key_date > to_date:
                break
            unavailable_quantity += rented_quantities[key_date]
            if key_date >= from_date:
                max_unavailable_qty = max(unavailable_quantity, max_unavailable_qty)

        return max_unavailable_qty

    def _get_active_rental_lines(
        self, from_date, to_date, ignored_soline_id=False, warehouse_id=False, **kwargs
    ):
        self.ensure_one()

        domain = [
            ('is_rental', '=', True),
            ('product_id', '=', self.id),
            ('state', '=', 'sale'),
        ]

        if ignored_soline_id:
            domain += [('id', '!=', ignored_soline_id)]

        if warehouse_id:
            domain += [('order_id.warehouse_id', '=', warehouse_id)]

        include_bounds = to_date == from_date
        domain += [
            ('return_date', '>=' if include_bounds and not kwargs.get('rental_pivot_date') else '>', from_date),
            '|', ('reservation_begin', '<=' if include_bounds else '<', to_date - timedelta(hours=self.preparation_time if kwargs.get('rental_pivot_date') else 0)),
                 ('qty_delivered', '>', 0),
        ]

        return self.env['sale.order.line'].search(domain)

    def _get_virtual_unavailable_qty_in_rent(self, pivot_date, **kwargs):
        """
        Return the quantity taken into account by the virtual available quantity
        prior to the pivot date but that will still be in rent past that date.

        :param datetime pivot_date:
        :param dict kwargs: search domain restrictions (ignored_soline_id, warehouse_id):
        """
        kwargs['rental_pivot_date'] = True
        active_lines = self._get_active_rental_lines(
            from_date=pivot_date, to_date=pivot_date, **kwargs
        )
        active_lines = active_lines.filtered(lambda line:
            line.order_id.rental_status in ('pickup', 'return')
                and (
                    not line.order_id.has_pickable_lines
                    or (
                        float_is_zero(line.qty_delivered, precision_rounding=line.product_uom.rounding)
                        and self.env.user.has_group('sale_stock_renting.group_rental_stock_picking')
                    )
                )
        )
        return sum(active_lines.mapped('product_uom_qty'))

    """
        Products with tracking (by serial number)
    """

    def _get_unavailable_lots(self, from_date, to_date=None, **kwargs):
        to_date = to_date or from_date
        return self._get_active_rental_lines(
            from_date, to_date, **kwargs
        ).mapped('unavailable_lot_ids')

    def action_view_rentals(self):
        result = super().action_view_rentals()
        result['context'].update({'sale_stock_renting_show_total_qty': 1})
        return result
