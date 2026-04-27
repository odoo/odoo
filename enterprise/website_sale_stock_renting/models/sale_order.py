# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_cart_and_free_qty(self, product, line=None):
        """ Override to take the rental product specificity into account

        For rental lines or product, the cart quantity is the maximum amount of the same product
        rented at the same time. The free quantity is the minimum available quantity during the same
        period plus the maximum cart quantity.

        Note: self.ensure_one()
        """
        if not product.rent_ok:
            return super()._get_cart_and_free_qty(product, line=line)
        from_date = self.rental_start_date and (
            self.rental_start_date - timedelta(hours=product.preparation_time))
        to_date = self.rental_return_date
        common_lines = self._get_common_product_lines(line=line, product=product)
        qty_available = product.with_context(
            from_date=from_date, to_date=to_date, warehouse_id=self.website_id.warehouse_id.id
        ).qty_available
        qty_available += product.with_context(
            warehouse_id=self.website_id.warehouse_id.id
        ).qty_in_rent
        product_rented_qties, product_key_dates = product._get_rented_quantities(
            from_date, to_date, domain=[('order_id', '!=', self.id)]
        )
        so_rented_qties, so_key_dates = common_lines._get_rented_quantities([from_date, to_date])
        current_cart_qty = max_cart_qty = 0
        current_available_qty = min_available_qty = qty_available
        key_dates = list(set(so_key_dates + product_key_dates))
        key_dates.sort()
        for i in range(1, len(key_dates)):
            start_dt = key_dates[i-1]
            if start_dt >= to_date:
                break
            current_cart_qty += so_rented_qties[start_dt]  # defaultdict
            current_available_qty -= product_rented_qties[start_dt]  # defaultdict
            max_cart_qty = max(max_cart_qty, current_cart_qty)
            min_available_qty = min(min_available_qty, current_available_qty - current_cart_qty)

        return max_cart_qty, max_cart_qty + min_available_qty

    def _build_warning_renting(self, product):
        """ Override to add the message regarding the preparation time
        """
        message = super()._build_warning_renting(product)
        reservation_begin = self.rental_start_date - timedelta(hours=product.preparation_time)
        if reservation_begin < fields.Datetime.now() <= self.rental_start_date:
            message += _("""Your rental product cannot be prepared on time, please rent later.""")

        return message

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        """ Override to ensure the cart has dates before checking the stock validity. """
        product = self.env['product.product'].browse(product_id)
        if product.rent_ok and not self.has_rented_products:
            if kwargs.get('start_date') and kwargs.get('end_date'):
                self.update({
                    'rental_start_date': kwargs.get('start_date'),
                    'rental_return_date': kwargs.get('end_date'),
                })
            else:
                self._rental_set_dates()
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

    def _is_valid_renting_dates(self):
        """ Override to take into account the preparation time."""
        res = super()._is_valid_renting_dates()
        rental_order_lines = self.order_line.filtered('reservation_begin')
        if not rental_order_lines or not res:
            return res
        max_padding_time = max(rental_order_lines.product_id.mapped('preparation_time'), default=0)
        initial_time = self.rental_start_date - timedelta(hours=max_padding_time)
        # 15 minutes of allowed time between adding the product to cart and paying it.
        return initial_time >= fields.Datetime.now() - timedelta(minutes=15)

    def _all_product_available(self):
        self.ensure_one()
        return super(SaleOrder, self.with_context(
            start_date=self.rental_start_date, end_date=self.rental_return_date
        ))._all_product_available()

    def _available_dates_for_renting(self):
        """Override to take into account the stock availability.
        """
        res = super()._available_dates_for_renting()
        if not res:
            return False
        for line in self.order_line:
            product = line.product_id
            if product.is_storable and not product.allow_out_of_stock_order:
                cart_qty, avl_qty = self._get_cart_and_free_qty(product, line=line)
                if cart_qty > avl_qty:
                    line._set_shop_warning_stock(cart_qty, max(avl_qty, 0))
                    return False
        return True
