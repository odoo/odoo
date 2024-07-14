# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


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
                lambda product: product.rent_ok and product.type == 'product'
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

    def _get_qty_in_rent_domain(self):
        """Allow precising the warehouse_id to get qty currently in rent."""
        if self.env.context.get('warehouse_id', False):
            return super()._get_qty_in_rent_domain() + [
                ('order_id.warehouse_id', '=', int(self.env.context.get('warehouse_id')))
            ]
        else:
            return super()._get_qty_in_rent_domain()

    def _get_unavailable_qty(self, fro, to=None, **kwargs):
        """Return max qty of self (unique) unavailable between fro and to.

        Doesn't count already returned quantities.
        :param datetime fro:
        :param datetime to:
        :param dict kwargs: search domain restrictions (ignored_soline_id, warehouse_id)
        """
        def unavailable_qty(so_line):
            return so_line.product_uom_qty - so_line.qty_returned

        begins_during_period, ends_during_period, covers_period = self._get_active_rental_lines(fro, to, **kwargs)
        active_lines_in_period = begins_during_period + ends_during_period
        max_qty_rented = 0

        # TODO is it more efficient to filter the records active in period
        # or to make another search on all the sale order lines???
        if active_lines_in_period:
            for date in (begins_during_period.mapped('reservation_begin') + [fro]):
                # If no soline in begins_during_period, we need to check at period beginning
                # how much products are rented.
                active_lines_at_date = active_lines_in_period.filtered(
                    lambda line: line.reservation_begin and line.reservation_begin <= date and line.return_date and line.return_date >= date)
                qty_rented_at_date = sum(active_lines_at_date.mapped(unavailable_qty))
                if qty_rented_at_date > max_qty_rented:
                    max_qty_rented = qty_rented_at_date

        qty_always_in_rent_during_period = sum(covers_period.mapped(unavailable_qty)) if covers_period else 0

        return max_qty_rented + qty_always_in_rent_during_period

    def _get_active_rental_lines(self, fro, to, **kwargs):
        self.ensure_one()

        Reservation = self.env['sale.order.line']
        domain = [
            ('is_rental', '=', True),
            ('product_id', '=', self.id),
            ('state', '=', 'sale'),
        ]

        ignored_soline_id = kwargs.get('ignored_soline_id', False)
        if ignored_soline_id:
            domain += [('id', '!=', ignored_soline_id)]

        warehouse_id = kwargs.get('warehouse_id', False)
        if warehouse_id:
            domain += [('order_id.warehouse_id', '=', warehouse_id)]

        if not to or fro == to:
            active_lines_at_time_fro = Reservation.search(domain + [
                ('reservation_begin', '<=', fro),
                ('return_date', '>=', fro)
            ])
            return Reservation, Reservation, active_lines_at_time_fro
        else:
            begins_during_period = Reservation.search(domain + [
                ('reservation_begin', '>', fro),
                ('reservation_begin', '<', to)])
            ends_during_period = Reservation.search(domain + [
                ('return_date', '>', fro),
                ('return_date', '<', to),
                ('id', 'not in', begins_during_period.ids)])
            covers_period = Reservation.search(domain + [
                ('reservation_begin', '<=', fro),
                ('return_date', '>=', to)])
            return begins_during_period, ends_during_period, covers_period

    """
        Products with tracking (by serial number)
    """

    def _get_unavailable_lots(self, fro=fields.Datetime.now(), to=None, **kwargs):
        begins_during_period, ends_during_period, covers_period = self._get_active_rental_lines(fro, to, **kwargs)
        return (begins_during_period + ends_during_period + covers_period).mapped('unavailable_lot_ids')

    def action_view_rentals(self):
        result = super().action_view_rentals()
        result['context'].update({'sale_stock_renting_show_total_qty': 1})
        return result
