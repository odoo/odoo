import json

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pickup_location_data = fields.Json()
    carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Delivery Method",
        check_company=True,
        help="Fill this field if you plan to invoice the shipping based on picking.",
    )
    delivery_message = fields.Char(
        copy=False,
        readonly=True,
    )
    delivery_set = fields.Boolean(compute="_compute_delivery_set")
    recompute_delivery_price = fields.Boolean(
        string="Delivery cost should be recomputed"
    )
    is_all_service = fields.Boolean(
        string="Service Product",
        compute="_compute_is_all_service",
    )
    shipping_weight = fields.Float(
        compute="_compute_shipping_weight",
        store=True,
        readonly=False,
    )

    def _compute_partner_shipping_id(self):
        """Override to reset the delivery address when a pickup location was selected."""
        super()._compute_partner_shipping_id()
        for order in self:
            if order.partner_shipping_id.is_pickup_location:
                order.partner_shipping_id = order.partner_id

    @api.depends("line_ids")
    def _compute_is_all_service(self):
        for so in self:
            so.is_all_service = all(
                line.product_id.type == "service"
                for line in so.line_ids.filtered(lambda x: not x.display_type)
            )

    def _get_amount_total_without_delivery(self):
        self.check_singleton()
        delivery_cost = sum(l.price_total for l in self.line_ids if l.is_delivery)
        return self.amount_total - delivery_cost

    @api.depends("line_ids")
    def _compute_delivery_set(self):
        for order in self:
            order.delivery_set = any(line.is_delivery for line in order.line_ids)

    @api.onchange("line_ids", "partner_id", "partner_shipping_id")
    def _onchange_recompute_delivery_price(self):
        self._flag_delivery_price_stale()

    def _flag_delivery_price_stale(self):
        for order in self:
            if order.line_ids.filtered("is_delivery"):
                order.recompute_delivery_price = True

    def _get_order_lines_price_updatable(self):
        """Exclude delivery lines from price list recomputation based on product instead of carrier"""
        lines = super()._get_order_lines_price_updatable()
        return lines.filtered(lambda line: not line.is_delivery)

    def _remove_delivery_line(self):
        """Remove delivery products from the sales orders"""
        # A pickup location is only ever meaningful for the carrier that was
        # selected when it was set; nothing else in this module keeps it in
        # sync with a carrier change, so clear it here, unconditionally,
        # every time the current delivery line is dropped.
        self.pickup_location_data = {}
        delivery_lines = self.line_ids.filtered("is_delivery")
        if not delivery_lines:
            return
        to_delete = delivery_lines.filtered(lambda x: x.qty_invoiced == 0)
        if not to_delete:
            raise UserError(
                _(
                    "You can not update the shipping costs on an order where it was already invoiced!\n\nThe following delivery lines (product, invoiced quantity and price) have already been processed:\n\n"
                )
                + "\n".join(
                    [
                        "- %s: %s x %s"
                        % (
                            line.product_id.with_context(
                                display_default_code=False
                            ).display_name,
                            line.qty_invoiced,
                            line.price_unit,
                        )
                        for line in delivery_lines
                    ]
                )
            )
        to_delete.unlink()

    def set_delivery_line(self, carrier, amount):
        self._remove_delivery_line()
        for order in self:
            order.carrier_id = carrier.id
            order._create_delivery_line(carrier, amount)
        return True

    def _set_pickup_location(self, pickup_location_data):
        """Set the pickup location on the current order.

        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        self.check_singleton()
        use_locations_fname = f"{self.carrier_id.delivery_type}_use_locations"
        if hasattr(self.carrier_id, use_locations_fname):
            use_location = getattr(self.carrier_id, use_locations_fname)
            if use_location and pickup_location_data:
                pickup_location = json.loads(pickup_location_data)
                self._check_pickup_location_data(pickup_location)
            else:
                pickup_location = None
            self.pickup_location_data = pickup_location

    def _check_pickup_location_data(self, pickup_location):
        """Ensure a pickup location payload carries the fields `_action_confirm` relies on.

        :param dict pickup_location: The decoded pickup location address.
        :raise UserError: If the payload is not an object or required fields are invalid.
        :return: None
        """
        if not isinstance(pickup_location, dict):
            raise UserError(_("The pickup location must contain address information."))
        missing_fnames = []
        for fname in ("street", "city", "zip_code", "country_code"):
            value = pickup_location.get(fname)
            if fname == "zip_code" and type(value) is int:
                value = str(value)
            if not isinstance(value, str) or not value.strip():
                missing_fnames.append(fname)
        for fname in ("name", "state"):
            value = pickup_location.get(fname)
            if value is not None and value is not False and not isinstance(value, str):
                missing_fnames.append(fname)
        if missing_fnames:
            raise UserError(
                _(
                    "The pickup location is missing required information: %s",
                    ", ".join(missing_fnames),
                )
            )

    def _get_pickup_locations(self, zip_code=None, country=None, **kwargs):
        """Return the pickup locations of the delivery method close to a given zip code.

        Use provided `zip_code` and `country` or the order's delivery address to determine the zip
        code and the country to use.

        :param str zip_code: The zip code to look up to, optional.
        :param res.country country: The country to look up to, required if `zip_code` is provided.
        :return: The close pickup locations data.
        :rtype: dict
        """
        self.check_singleton()
        if zip_code:
            assert country  # country is required if zip_code is provided.
            partner_address = self.env["res.partner"].new(
                {
                    "active": False,
                    "country_id": country.id,
                    "zip": zip_code,
                }
            )
        else:
            partner_address = self.partner_shipping_id
        try:
            error = {
                "error": _("No pick-up points are available for this delivery address.")
            }
            function_name = f"_{self.carrier_id.delivery_type}_get_close_locations"
            if not hasattr(self.carrier_id, function_name):
                return error
            pickup_locations = getattr(self.carrier_id, function_name)(
                partner_address, **kwargs
            )
            if not pickup_locations:
                return error
            return {"pickup_locations": pickup_locations}
        except UserError as e:
            return {"error": str(e)}

    def action_view_delivery_wizard(self):
        view_id = self.env.ref("delivery.choose_delivery_carrier_view_form").id
        if self.env.context.get("carrier_recompute"):
            name = _("Update shipping cost")
            carrier = self.carrier_id
        else:
            name = _("Add a shipping method")
            shipping_partner_id = self.with_company(self.company_id).partner_shipping_id
            carrier_property = (
                shipping_partner_id.property_delivery_carrier_id.filtered("active")
                or shipping_partner_id.commercial_partner_id.property_delivery_carrier_id.filtered(
                    "active"
                )
            )
            carrier = carrier_property._filtered_available_carriers(
                self.partner_shipping_id, self
            )
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "choose.delivery.carrier",
            "view_id": view_id,
            "views": [(view_id, "form")],
            "target": "new",
            "context": {
                "default_order_id": self.id,
                "default_carrier_id": carrier.id,
                "default_total_weight": self._get_estimated_weight(),
            },
        }

    def _get_pickup_address_values(self, location):
        self.check_singleton()
        self._check_pickup_location_data(location)
        recipient = self.partner_shipping_id
        while recipient.is_pickup_location and recipient.parent_id:
            recipient = recipient.parent_id
        country = self.env["res.country"].search(
            [("code", "=", location["country_code"].strip().upper())],
            limit=1,
        )
        if not country:
            raise UserError(_("The pickup location country is invalid."))
        state = self.env["res.country.state"]
        if location.get("state"):
            state = state.search(
                [
                    ("code", "=", location["state"]),
                    ("country_id", "=", country.id),
                ],
                limit=1,
            )
        return {
            "parent_id": recipient.id,
            "type": "delivery",
            "name": location.get("name") or recipient.name,
            "street": location["street"],
            "city": location["city"],
            "state_id": state.id,
            "zip": str(location["zip_code"]),
            "country_id": country.id,
            "is_pickup_location": True,
        }

    def _action_confirm(self):
        for order in self:
            if not order.pickup_location_data:
                continue
            address_values = order._get_pickup_address_values(
                order.pickup_location_data
            )
            recipient = order.env["res.partner"].browse(address_values["parent_id"])
            phone = recipient._phone_get_number()
            shipping_partner = order.env["res.partner"].search(  # noqa: E8507 - resolve each order's recipient-owned pickup address
                [(field, "=", value) for field, value in address_values.items()],
                limit=1,
            ) or order.env["res.partner"].create(
                {
                    **address_values,
                    "email": recipient.email,
                    "phone_ids": [Command.link(phone.id)] if phone else [],
                }
            )
            if phone_values := shipping_partner._prepare_phone_replacement_vals(phone):
                shipping_partner.write(phone_values)
            order.with_context(update_delivery_shipping_partner=True).write(
                {"partner_shipping_id": shipping_partner}
            )
        return super()._action_confirm()

    def _prepare_delivery_line_vals(self, carrier, price_unit):
        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id._filter_taxes_by_company(self.company_id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        # Build the sales order line values

        if carrier.product_id.description_sale:
            so_description = "%s: %s" % (
                carrier.name,
                carrier.product_id.description_sale,
            )
        else:
            so_description = carrier.name
        values = {
            "order_id": self.id,
            "name": so_description,
            "price_unit": price_unit,
            # `product_qty`, the writable quantity: `product_uom_qty` is computed
            # from it and discards anything written here (see
            # base_order/models/order_line_amount_mixin.py).
            "product_qty": 1,
            "product_id": carrier.product_id.id,
            "tax_ids": [(6, 0, taxes_ids)],
            "is_delivery": True,
        }
        if carrier.free_over and self.currency_id.is_zero(price_unit):
            values["name"] = _("%s\nFree Shipping", values["name"])
        if self.line_ids:
            values["sequence"] = self.line_ids[-1].sequence + 1
        return values

    def _create_delivery_line(self, carrier, price_unit):
        values = self._prepare_delivery_line_vals(carrier, price_unit)
        return self.env["sale.order.line"].sudo().create(values)

    @api.depends("line_ids.product_uom_qty", "line_ids.product_uom_id")
    def _compute_shipping_weight(self):
        for order in self:
            order.shipping_weight = order._get_estimated_weight()

    def _get_estimated_weight(self):
        self.check_singleton()
        weight = 0.0
        for order_line in self.line_ids.filtered(
            lambda l: (
                l.product_id.type == "consu"
                and not l.is_delivery
                and not l.display_type
                and l.product_uom_qty > 0
            )
        ):
            weight += order_line.product_uom_qty * order_line.product_id.weight
        return weight

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """Override of `sale` to recompute the delivery prices.

        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        price_unit = super()._update_order_line_info(product_id, quantity, **kwargs)
        self._flag_delivery_price_stale()
        return price_unit
