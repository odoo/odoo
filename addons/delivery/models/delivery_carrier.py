import logging
import re

import psycopg

from odoo import SUPERUSER_ID, Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


_debug = DebugLog(__name__)


class DeliveryCarrier(models.Model):
    """Shipping carrier: rate computation and delivery-method configuration."""

    _name = "delivery.carrier"
    _inherit = ["mixin.credential.holder", "mixin.integration.connected"]
    _description = "Shipping Methods"
    _order = "sequence, id"
    _credential_holder_field = "carrier_credential_id"
    _credential_purpose = "delivery:carrier"

    # To add an external provider: inherit this model, extend the
    # "delivery_type" selection with a ('<my_provider>', 'My Provider') pair,
    # and add <my_provider>_rate_shipment, <my_provider>_send_shipping,
    # <my_provider>_get_tracking_link, <my_provider>_cancel_shipment and
    # _<my_provider>_get_default_custom_package_code (documented hereunder).

    # -------------------------------- #
    # Internals for shipping providers #
    # -------------------------------- #

    name = fields.Char(
        string="Delivery Method",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=10,
        help="Determine the display order",
    )
    # This field will be overwritten by internal shipping providers by adding their own type (ex: 'fedex')
    delivery_type = fields.Selection(
        selection=[("base_on_rule", "Based on Rules"), ("fixed", "Fixed Price")],
        string="Provider",
        default="fixed",
        required=True,
    )
    allow_cash_on_delivery = fields.Boolean(
        string="Cash on Delivery",
        help="Allow customers to choose Cash on Delivery as their payment method.",
    )
    integration_level = fields.Selection(
        selection=[
            ("rate", "Get Rate"),
            ("rate_and_ship", "Get Rate and Create Shipment"),
        ],
        default="rate_and_ship",
        help="Action while validating Delivery Orders",
    )
    prod_environment = fields.Boolean(
        string="Environment",
        help="Set to True if your credentials are certified for production.",
    )
    debug_logging = fields.Boolean(
        string="Debug logging",
        help="Log requests in order to ease debugging",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="product_id.company_id",
        string="Company",
        readonly=False,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Delivery Product",
        required=True,
        ondelete="restrict",
    )
    tracking_url = fields.Char(
        string="Tracking Link",
        help="This option adds a link for the customer in the portal to track their package easily. Use <shipmenttrackingnumber> as a placeholder in your URL.",
    )
    currency_id = fields.Many2one(related="product_id.currency_id")

    invoice_policy = fields.Selection(
        selection=[("estimated", "Estimated cost")],
        string="Invoicing Policy",
        default="estimated",
        required=True,
        help="Estimated Cost: the customer will be invoiced the estimated cost of the shipping.",
    )

    country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="delivery_carrier_country_rel",
        column1="carrier_id",
        column2="country_id",
        string="Countries",
    )
    state_ids = fields.Many2many(
        comodel_name="res.country.state",
        relation="delivery_carrier_state_rel",
        column1="carrier_id",
        column2="state_id",
        string="States",
    )
    zip_prefix_ids = fields.Many2many(
        comodel_name="delivery.zip.prefix",
        relation="delivery_zip_prefix_rel",
        column1="carrier_id",
        column2="zip_prefix_id",
        string="Zip Prefixes",
        help="Prefixes of zip codes that this carrier applies to. Note that regular expressions can be used to support countries with varying zip code lengths, i.e. '$' can be added to end of prefix to match the exact zip (e.g. '100$' will only match '100' and not '1000')",
    )

    max_weight = fields.Float(
        help="If the total weight of the order is over this weight, the method won't be available."
    )
    # Every carrier's secrets rest in credential.credential, through
    # mixin.credential.holder. The carriers keep their own field NAMES -- they
    # are in the views and in every request builder -- and declare them as doors
    # in `_CREDENTIAL_FIELDS`.
    #
    # The vault field a given secret maps to is the carrier's decision, because
    # the shapes differ: DHL has a key and a secret, Sendcloud has one key,
    # Easypost has one per environment. `api_key`/`api_secret` take a pair, and
    # `credential_data` takes anything that is neither.
    carrier_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds this carrier's API secrets.",
    )

    weight_uom_name = fields.Char(
        string="Weight unit of measure label",
        compute="_compute_weight_uom_name",
    )
    max_volume = fields.Float(
        help="If the total volume of the order is over this volume, the method won't be available."
    )
    volume_uom_name = fields.Char(
        string="Volume unit of measure label",
        compute="_compute_volume_uom_name",
    )
    must_have_tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_delivery_carrier_must_have_rel",
        string="Must Have Tags",
        help="The method is available only if at least one product of the order has one of these tags.",
    )
    excluded_tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_delivery_carrier_excluded_rel",
        string="Excluded Tags",
        help="The method is NOT available if at least one product of the order has one of these tags.",
    )

    carrier_description = fields.Text(
        translate=True,
        help="A description of the delivery method that you want to communicate to your customers on the Sales Order and sales confirmation email."
        "E.g. instructions for customers to follow.",
    )

    margin = fields.Float(help="This percentage will be added to the shipping price.")
    fixed_margin = fields.Float(
        help="This fixed amount will be added to the shipping price."
    )
    free_over = fields.Boolean(
        string="Free if order amount is above",
        default=False,
        help="If the order total amount (shipping excluded) is above or equal to this value, the customer benefits from a free shipping",
    )
    amount = fields.Float(
        default=1000,
        help="Amount of the order to benefit from a free shipping, expressed in the company currency",
    )

    can_generate_return = fields.Boolean(compute="_compute_can_generate_return")
    return_label_on_delivery = fields.Boolean(
        string="Generate Return Label",
        help="The return label is automatically generated at the delivery.",
    )
    get_return_label_from_portal = fields.Boolean(
        string="Return Label Accessible from Customer Portal",
        help="The return label can be downloaded by the customer from the customer portal.",
    )

    supports_shipping_insurance = fields.Boolean(
        compute="_compute_supports_shipping_insurance"
    )
    shipping_insurance = fields.Integer(
        string="Insurance Percentage",
        default=0,
        help="Shipping insurance is a service which may reimburse senders whose parcels are lost, stolen, and/or damaged in transit.",
    )

    price_rule_ids = fields.One2many(
        comodel_name="delivery.price.rule",
        inverse_name="carrier_id",
        string="Pricing Rules",
        copy=True,
    )

    _margin_not_under_100_percent = models.Constraint(
        "CHECK (margin >= -1)",
        "Margin cannot be lower than -100%",
    )
    _shipping_insurance_is_percentage = models.Constraint(
        "CHECK(shipping_insurance >= 0 AND shipping_insurance <= 100)",
        "The shipping insurance must be a percentage between 0 and 100.",
    )

    @api.constrains("must_have_tag_ids", "excluded_tag_ids")
    def _integration_connection_service(self) -> tuple[str, str, str]:
        self.check_singleton()
        label = dict(
            self._fields["delivery_type"]._description_selection(self.env)
        ).get(self.delivery_type, self.delivery_type)
        return (
            f"delivery_{self.delivery_type}",
            self.env._("Delivery: %s", label),
            "delivery",
        )

    def _check_tags(self):
        for carrier in self:
            if carrier.must_have_tag_ids & carrier.excluded_tag_ids:
                raise UserError(
                    _(
                        "Carrier %s cannot have the same tag in both Must Have Tags and Excluded Tags."
                    )
                    % carrier.name
                )

    def _compute_weight_uom_name(self):
        self.weight_uom_name = self.env[
            "product.template"
        ]._get_weight_uom_name_from_ir_config_parameter()

    def _compute_volume_uom_name(self):
        self.volume_uom_name = self.env[
            "product.template"
        ]._get_volume_uom_name_from_ir_config_parameter()

    @api.depends("delivery_type")
    def _compute_can_generate_return(self):
        for carrier in self:
            carrier.can_generate_return = False

    @api.depends("delivery_type")
    def _compute_supports_shipping_insurance(self):
        for carrier in self:
            carrier.supports_shipping_insurance = False

    def toggle_prod_environment(self):
        for c in self:
            c.prod_environment = not c.prod_environment

    def toggle_debug(self):
        for c in self:
            c.debug_logging = not c.debug_logging

    def install_more_provider(self):
        exclude_apps = [
            "delivery_barcode",
            "delivery_stock_picking_batch",
            "delivery_iot",
        ]
        return {
            "name": _("New Providers"),
            "res_model": "ir.module.module",
            "view_mode": "kanban,list",
            "views": [
                (self.env.ref("delivery.delivery_provider_module_kanban").id, "kanban"),
                (self.env.ref("delivery.delivery_provider_module_list").id, "list"),
            ],
            "domain": [
                ["name", "=like", "delivery_%"],
                ["name", "not in", exclude_apps],
            ],
            "type": "ir.actions.act_window",
            "help": _("""<p class="o_view_nocontent">
                    Buy Odoo Enterprise now to get more providers.
                </p>"""),
        }

    def _is_available_for_order(self, order):
        self.check_singleton()
        order.check_singleton()
        if not self._match(order.partner_shipping_id, order):
            return False

        if self.delivery_type == "base_on_rule":
            return self.rate_shipment(order).get("success")

        return True

    def _filtered_available_carriers(self, partner, source):
        _debug.pipeline(
            "carriers_filter_enter", carriers=self, partner=partner.id, source=source
        )
        return self.filtered(lambda c: c._match(partner, source))

    def _match(self, partner, source):
        self.check_singleton()
        _debug.logic(
            "carrier_match_enter",
            carrier=self.id,
            partner=partner.id,
            source=source,
        )
        return (
            self._match_address(partner)
            and self._match_must_have_tags(source)
            and self._match_excluded_tags(source)
            and self._match_weight(source)
            and self._match_volume(source)
        )

    def _match_address(self, partner):
        self.check_singleton()
        if self.country_ids and partner.country_id not in self.country_ids:
            _debug.logic(
                "carrier_rejected",
                carrier=self.id,
                by="country",
                partner_country=partner.country_id.id,
            )
            return False
        if self.state_ids and partner.state_id not in self.state_ids:
            _debug.logic(
                "carrier_rejected",
                carrier=self.id,
                by="state",
                partner_state=partner.state_id.id,
            )
            return False
        if self.zip_prefix_ids:
            regex = re.compile(
                "|".join(
                    [
                        "^" + zip_prefix
                        for zip_prefix in self.zip_prefix_ids.mapped("name")
                    ]
                )
            )
            if not partner.zip or not re.match(regex, partner.zip.upper()):
                _debug.logic(
                    "carrier_rejected",
                    carrier=self.id,
                    by="zip_prefix",
                    partner_zip=partner.zip or "",
                )
                return False
        return True

    def _match_must_have_tags(self, source):
        self.check_singleton()
        if source._name == "sale.order":
            products = source.line_ids.product_id
        elif source._name == "stock.picking":
            products = source.move_ids.with_prefetch().mapped("product_id")
        else:
            raise UserError(_("Invalid source document type"))
        _debug.logic(
            "carrier_match_must_have_tags",
            carrier=self.id,
            required=self.must_have_tag_ids,
            products=products,
        )
        return not self.must_have_tag_ids or any(
            tag in products.all_product_tag_ids for tag in self.must_have_tag_ids
        )

    def _match_excluded_tags(self, source):
        self.check_singleton()
        if source._name == "sale.order":
            products = source.line_ids.product_id
        elif source._name == "stock.picking":
            products = source.move_ids.with_prefetch().mapped("product_id")
        else:
            raise UserError(_("Invalid source document type"))
        _debug.logic(
            "carrier_match_excluded_tags",
            carrier=self.id,
            excluded=self.excluded_tag_ids,
            products=products,
        )
        return not any(
            tag in products.all_product_tag_ids for tag in self.excluded_tag_ids
        )

    def _match_weight(self, source):
        self.check_singleton()
        if source._name == "sale.order":
            total_weight = sum(
                line.product_id.weight * line.product_uom_qty
                for line in source.line_ids
            )
        elif source._name == "stock.picking":
            total_weight = sum(
                move.product_id.weight * move.product_uom_qty
                for move in source.move_ids
            )
        else:
            raise UserError(_("Invalid source document type"))
        _debug.logic(
            "carrier_match_weight",
            carrier=self.id,
            total=total_weight,
            max=self.max_weight,
        )
        return not self.max_weight or total_weight <= self.max_weight

    def _match_volume(self, source):
        self.check_singleton()
        if source._name == "sale.order":
            total_volume = sum(
                line.product_id.volume * line.product_uom_qty
                for line in source.line_ids
            )
        elif source._name == "stock.picking":
            total_volume = sum(
                move.product_id.volume * move.product_uom_qty
                for move in source.move_ids
            )
        else:
            raise UserError(_("Invalid source document type"))
        _debug.logic(
            "carrier_match_volume",
            carrier=self.id,
            total=total_volume,
            max=self.max_volume,
        )
        return not self.max_volume or total_volume <= self.max_volume

    @api.onchange("integration_level")
    def _onchange_integration_level(self):
        if self.integration_level == "rate":
            self.invoice_policy = "estimated"

    @api.onchange("can_generate_return")
    def _onchange_can_generate_return(self):
        if not self.can_generate_return:
            self.return_label_on_delivery = False

    @api.onchange("return_label_on_delivery")
    def _onchange_return_label_on_delivery(self):
        if not self.return_label_on_delivery:
            self.get_return_label_from_portal = False

    @api.onchange("country_ids")
    def _onchange_country_ids(self):
        self.state_ids -= self.state_ids.filtered(
            lambda state: state._origin.id not in self.country_ids.state_ids.ids
        )
        if not self.country_ids:
            self.zip_prefix_ids = [Command.clear()]

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", carrier.name))
            for carrier, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        # ``copy_data`` renames ``name`` in the duplicating user's language
        # only; without this the copy would keep the source record's exact
        # ``name`` in every other language.
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def _get_delivery_type(self):
        """Return the delivery type.

        This method needs to be overridden by a delivery carrier module if the delivery type is not
        stored on the field `delivery_type`.
        """
        self.check_singleton()
        return self.delivery_type

    def _apply_margins(self, price, order=False):
        _debug.logic(
            "carrier_margin_apply", carrier=self.id, price=price, margin=self.margin
        )
        self.check_singleton()
        if self.delivery_type == "fixed":
            return float(price)
        fixed_margin_in_sale_currency = (
            self._get_converted_price(order, self.fixed_margin, "company_to_pricelist")
            if order
            else self.fixed_margin
        )
        return float(price) * (1.0 + self.margin) + fixed_margin_in_sale_currency

    # -------------------------- #
    # API for external providers #
    # -------------------------- #

    def rate_shipment(self, order):
        """Compute the price of the order shipment

        :param order: record of sale.order
        :returns: a dict with structure
          ::

            {'success': boolean,
             'price': a float,
             'error_message': a string containing an error message,
             'warning_message': a string containing a warning message,
             'carrier_price': a float, present on the success path only}
        :rtype: dict
        """
        # TODO maybe the currency code?
        self.check_singleton()
        _debug.pipeline(
            "rate_shipment_enter",
            carrier=self.id,
            delivery_type=self.delivery_type,
            order=order.id,
        )
        if hasattr(self, "%s_rate_shipment" % self.delivery_type):
            res = getattr(self, "%s_rate_shipment" % self.delivery_type)(order)
            # apply fiscal position
            company = self.company_id or order.company_id or self.env.company
            res["price"] = self.product_id._get_tax_included_unit_price(
                company,
                company.currency_id,
                order.date_order,
                "sale",
                fiscal_position=order.fiscal_position_id,
                product_price_unit=res["price"],
                product_currency=company.currency_id,
            )
            # apply margin on computed price
            res["price"] = self._apply_margins(res["price"], order)
            # save the real price in case a free_over rule overide it to 0
            res["carrier_price"] = res["price"]
            # free when order is large enough
            amount_without_delivery = order._get_amount_total_without_delivery()
            if (
                res["success"]
                and self.free_over
                and self.delivery_type != "base_on_rule"
                and self._get_converted_price(
                    order, amount_without_delivery, "pricelist_to_company"
                )
                >= self.amount
            ):
                res["warning_message"] = _(
                    "The shipping is free since the order amount exceeds %.2f.",
                    self.amount,
                )
                _debug.logic(
                    "shipping_free_over",
                    carrier=self.id,
                    order=order.id,
                    threshold=self.amount,
                )
                res["price"] = 0.0
            _debug.pipeline(
                "rate_shipment_done",
                carrier=self.id,
                order=order.id,
                success=res["success"],
                price=res["price"],
            )
            return res
        else:
            _debug.logic(
                "rate_shipment_unsupported",
                carrier=self.id,
                delivery_type=self.delivery_type,
            )
            return {
                "success": False,
                "price": 0.0,
                "error_message": _("Error: this delivery method is not available."),
                "warning_message": False,
            }

    def log_xml(self, xml_string, func):
        self.check_singleton()

        if self.debug_logging:
            self.env.flush_all()
            db_name = self.env.cr.dbname

            # Use a new cursor to avoid rollback that could be caused by an upper method
            try:
                db_registry = Registry(db_name)
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    IrLogging = env["ir.logging"]
                    IrLogging.sudo().create(
                        {
                            "name": "delivery.carrier",
                            "type": "server",
                            "dbname": db_name,
                            "level": "DEBUG",
                            "message": xml_string,
                            "path": self.delivery_type,
                            "func": func,
                            "line": 1,
                        }
                    )
            except psycopg.Error:
                pass

    # ------------------------------------------------ #
    # Fixed price shipping, aka a very simple provider #
    # ------------------------------------------------ #

    fixed_price = fields.Float(
        compute="_compute_fixed_price",
        inverse="_inverse_fixed_price",
        store=True,
    )

    @api.depends("product_id.list_price", "product_id.product_tmpl_id.list_price")
    def _compute_fixed_price(self):
        for carrier in self:
            carrier.fixed_price = carrier.product_id.list_price

    def _inverse_fixed_price(self):
        for carrier in self:
            carrier.product_id.list_price = carrier.fixed_price

    def fixed_rate_shipment(self, order):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            _debug.logic(
                "rate_refused",
                carrier=self.id,
                reason="address_not_matched",
                order=order.id,
                rating="fixed_rate_shipment",
            )
            return {
                "success": False,
                "price": 0.0,
                "error_message": _(
                    "Error: this delivery method is not available for this address."
                ),
                "warning_message": False,
            }
        price = order.pricelist_id._get_product_price(self.product_id, 1.0)
        return {
            "success": True,
            "price": price,
            "error_message": False,
            "warning_message": False,
        }

    # ----------------------------------- #
    # Based on rule delivery type methods #
    # ----------------------------------- #

    def base_on_rule_rate_shipment(self, order):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            _debug.logic(
                "rate_refused",
                carrier=self.id,
                reason="address_not_matched",
                order=order.id,
                rating="base_on_rule_rate_shipment",
            )
            return {
                "success": False,
                "price": 0.0,
                "error_message": _(
                    "Error: this delivery method is not available for this address."
                ),
                "warning_message": False,
            }

        try:
            price_unit = self._get_price_available(order)
        except UserError as e:
            _debug.logic(
                "rate_refused",
                carrier=self.id,
                reason="price_rule_error",
                order=order.id,
            )
            return {
                "success": False,
                "price": 0.0,
                "error_message": e.args[0],
                "warning_message": False,
            }

        price_unit = self._get_converted_price(
            order, price_unit, "company_to_pricelist"
        )

        return {
            "success": True,
            "price": price_unit,
            "error_message": False,
            "warning_message": False,
        }

    def _get_conversion_currencies(self, order, conversion):
        company_currency = (
            self.company_id or self.env["res.company"]._get_main_company()
        ).currency_id
        pricelist_currency = order.currency_id

        if conversion == "company_to_pricelist":
            return company_currency, pricelist_currency
        elif conversion == "pricelist_to_company":
            return pricelist_currency, company_currency
        return None

    def _get_converted_price(self, order, price, conversion):
        from_currency, to_currency = self._get_conversion_currencies(order, conversion)
        if from_currency.id == to_currency.id:
            return price
        return from_currency._convert(
            price,
            to_currency,
            order.company_id,
            order.date_order or fields.Date.today(),
        )

    def _get_price_available(self, order):
        self.check_singleton()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = wv = 0
        for line in order.line_ids:
            if line.state == "cancel":
                continue
            if not line.product_id or line.is_delivery:
                continue
            if line.product_id.type in {"service", "combo"}:
                continue
            # `product_uom_qty` IS the line quantity already converted to the
            # product's reference UoM, which is the unit `weight`/`volume` are
            # expressed in. Running it through `_get_quantity_in_unit` again converted
            # a second time and inflated every weight/volume on a line whose UoM
            # differs from the product's (12 Units sold as 1 Dozen weighed as 144).
            qty = line.product_uom_qty
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            wv += (
                (line.product_id.weight or 0.0) * (line.product_id.volume or 0.0) * qty
            )
            quantity += qty
        total = order._get_amount_total_without_delivery()

        total = self._get_converted_price(order, total, "pricelist_to_company")
        # weight is either,
        # 1- weight chosen by user in choose.delivery.carrier wizard passed by context
        # 2- saved weight to use on sale order
        # 3- total order line weight as fallback
        weight = self.env.context.get("order_weight") or order.shipping_weight or weight
        _debug.logic(
            "price_available_inputs",
            carrier=self.id,
            order=order.id,
            total=total,
            weight=weight,
            volume=volume,
            quantity=quantity,
        )
        return self._get_price_from_picking(total, weight, volume, quantity, wv=wv)

    def _get_price_dict(self, total, weight, volume, quantity, wv=0.0):
        """Hook allowing to retrieve dict to be used in _get_price_from_picking() function.
        Hook to be overridden when we need to add some field to product and use it in variable factor from price rules.

        :return: The price factors used to evaluate the price rules.
        :rtype: dict
        """
        return {
            "price": total,
            "volume": volume,
            "weight": weight,
            "wv": wv or volume * weight,
            "quantity": quantity,
        }

    def _get_price_from_picking(self, total, weight, volume, quantity, wv=0.0):
        price = 0.0
        criteria_found = False
        price_dict = self._get_price_dict(total, weight, volume, quantity, wv=wv)
        for line in self.price_rule_ids:
            test = safe_eval(
                line.variable + line.operator + str(line.max_value), price_dict
            )
            if test:
                price = (
                    line.list_base_price
                    + line.list_price * price_dict[line.variable_factor]
                )
                criteria_found = True
                break
        if not criteria_found:
            raise UserError(_("Not available for current order"))

        return price
