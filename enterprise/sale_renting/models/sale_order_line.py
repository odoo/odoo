# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone, UTC

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.tools import format_datetime, format_time


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Stored because a product could have been rent_ok when added to the SO but then updated
    is_rental = fields.Boolean(compute='_compute_is_rental', store=True, precompute=True, readonly=False, copy=True)

    qty_returned = fields.Float("Returned", default=0.0, copy=False)
    start_date = fields.Datetime(related='order_id.rental_start_date')
    return_date = fields.Datetime(related='order_id.rental_return_date')
    reservation_begin = fields.Datetime(
        string="Pickup date - padding time", compute='_compute_reservation_begin', store=True)

    is_product_rentable = fields.Boolean(related='product_id.rent_ok', depends=['product_id'])

    @api.depends('order_id.rental_start_date')
    def _compute_reservation_begin(self):
        lines = self.filtered('is_rental')
        for line in lines:
            line.reservation_begin = line.order_id.rental_start_date
        (self - lines).reservation_begin = None

    @api.onchange('qty_delivered')
    def _onchange_qty_delivered(self):
        """When picking up more than reserved, reserved qty is updated"""
        if self.qty_delivered > self.product_uom_qty:
            self.product_uom_qty = self.qty_delivered

    @api.depends('is_rental')
    def _compute_qty_delivered_method(self):
        """Allow modification of delivered qty without depending on stock moves."""
        rental_lines = self.filtered('is_rental')
        super(SaleOrderLine, self - rental_lines)._compute_qty_delivered_method()
        rental_lines.qty_delivered_method = 'manual'

    @api.depends('is_rental')
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()

    @api.depends('product_id')
    def _compute_is_rental(self):
        for line in self:
            line.is_rental = line.is_product_rentable and line.env.context.get('in_rental_app')

    @api.depends('is_rental')
    def _compute_product_updatable(self):
        rental_lines = self.filtered('is_rental')
        super(SaleOrderLine, self - rental_lines)._compute_product_updatable()
        rental_lines.product_updatable = True

    def _compute_pricelist_item_id(self):
        """Discard pricelist item computation for rental lines.

        This will disable the standard discount computation because no pricelist rule was found.
        """
        rental_lines = self.filtered('is_rental')
        super(SaleOrderLine, self - rental_lines)._compute_pricelist_item_id()
        rental_lines.pricelist_item_id = False

    _sql_constraints = [
        ('rental_stock_coherence',
            "CHECK(NOT is_rental OR qty_returned <= qty_delivered)",
            "You cannot return more than what has been picked up."),
    ]

    def _get_sale_order_line_multiline_description_sale(self):
        """Add Rental information to the SaleOrderLine name."""
        res = super()._get_sale_order_line_multiline_description_sale()
        if self.is_rental:
            self.order_id._rental_set_dates()
            res += self._get_rental_order_line_description()
        return res

    def _get_rental_order_line_description(self):
        tz = self._get_tz()
        start_date = self.order_id.rental_start_date
        return_date = self.order_id.rental_return_date
        env = self.with_context(use_babel=True).env
        if start_date and return_date\
           and start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()\
               == return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date():
            # If return day is the same as pickup day, don't display return_date Y/M/D in description.
            return_date_part = format_time(env, return_date, tz=tz, time_format=False)
        else:
            return_date_part = format_datetime(env, return_date, tz=tz, dt_format=False)
        start_date_part = format_datetime(env, start_date, tz=tz, dt_format=False)
        return _(
            "\n%(from_date)s to %(to_date)s", from_date=start_date_part, to_date=return_date_part
        )

    def _use_template_name(self):
        """ Avoid the template line description in order to add the rental period on the SOL. """
        if self.is_rental:
            return False
        return super()._use_template_name()

    def _generate_delay_line(self, qty_returned):
        """Generate a sale order line representing the delay cost due to the late return.

        :param float qty_returned: returned quantity
        """
        self.ensure_one()

        self = self.with_company(self.company_id)
        duration = fields.Datetime.now() - self.return_date

        delay_price = self.product_id._compute_delay_price(duration)
        if delay_price <= 0.0:
            return

        # migrate to a function on res_company get_extra_product?
        delay_product = self.company_id.extra_product
        if not delay_product:
            delay_product = self.env['product.product'].with_context(active_test=False).search(
                [('default_code', '=', 'RENTAL'), ('type', '=', 'service')], limit=1)
            if not delay_product:
                delay_product = self.env['product.product'].create({
                    "name": "Rental Delay Cost",
                    "standard_price": 0.0,
                    "type": 'service',
                    "default_code": "RENTAL",
                    "purchase_ok": False,
                })
                # Not set to inactive to allow users to put it back in the settings
                # In case they removed it.
            self.company_id.extra_product = delay_product

        if not delay_product.active:
            return

        delay_price = self._convert_to_sol_currency(delay_price, self.product_id.currency_id)

        order_line_vals = self._prepare_delay_line_vals(delay_product, delay_price * qty_returned)

        self.order_id.write({
            'order_line': [Command.create(order_line_vals)],
        })

    def _prepare_delay_line_vals(self, delay_product, delay_price):
        """Prepare values of delay line.

        :param product.product delay_product: Product used for the delay_line
        :param float delay_price: Price of the delay line

        :return: sale.order.line creation values
        :rtype dict:
        """
        delay_line_description = self._get_delay_line_description()
        return {
            'name': delay_line_description,
            'product_id': delay_product.id,
            'product_uom_qty': 1,
            'qty_delivered': 1,
            'price_unit': delay_price,
        }

    def _get_delay_line_description(self):
        # Shouldn't tz be taken from self.order_id.user_id.tz ?
        tz = self._get_tz()
        env = self.with_context(use_babel=True).env
        expected_date = format_datetime(env, self.return_date, tz=tz, dt_format=False)
        now = format_datetime(env, fields.Datetime.now(), tz=tz, dt_format=False)
        return "%s\n%s\n%s" % (
            self.product_id.name,
            _("Expected: %(date)s", date=expected_date),
            _("Returned: %(date)s", date=now),
        )

    def _get_tz(self):
        return self.env.context.get('tz') or self.env.user.tz or 'UTC'

    def _get_pricelist_price(self):
        """ Custom price computation for rental lines.

        The displayed price will only be the price given by the product.pricing rules matching the
        given line information (product, period, pricelist, ...).
        """
        self.ensure_one()
        if self.is_rental:
            self.order_id._rental_set_dates()
            return self.order_id.pricelist_id._get_product_price(
                self.product_id.with_context(**self._get_product_price_context()),
                self.product_uom_qty or 1.0,
                currency=self.currency_id,
                uom=self.product_uom,
                date=self.order_id.date_order or fields.Date.today(),
                start_date=self.start_date,
                end_date=self.return_date,
            )
        return super()._get_pricelist_price()

    # === PRICE COMPUTING HOOKS === #

    def _lines_without_price_recomputation(self):
        """ Override to filter out rental lines and allow the recomputation for these SOL. """
        res = super()._lines_without_price_recomputation()
        return res.filtered(lambda l: not l.is_rental)
