from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_is_zero, float_round
from odoo.tools.misc import groupby

from .delivery_request_objects import DeliveryCommodity, DeliveryPackage

_debug = DebugLog(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    invoice_policy = fields.Selection(
        selection_add=[("real", "Real cost")],
        ondelete={"real": "set default"},
        help="Estimated Cost: the customer will be invoiced the estimated cost of the shipping.\n"
        "Real Cost: the customer will be invoiced the real cost of the shipping, the cost of the"
        "shipping will be updated on the SO after the delivery.",
    )

    route_ids = fields.Many2many(
        comodel_name="stock.route",
        relation="stock_route_shipping",
        column1="shipping_id",
        column2="route_id",
        string="Routes",
        domain=[("shipping_selectable", "=", True)],
    )

    def send_shipping(self, pickings):
        _debug.pipeline("carrier_send_shipping", carrier=self.id, pickings=pickings)
        self.check_singleton()
        if hasattr(self, "%s_send_shipping" % self.delivery_type):
            return getattr(self, "%s_send_shipping" % self.delivery_type)(pickings)
        return None

    def get_return_label(self, pickings, tracking_number=None, origin_date=None):
        _debug.pipeline("carrier_return_label", carrier=self.id, pickings=pickings)
        self.check_singleton()
        if self.can_generate_return:
            res = getattr(self, "%s_get_return_label" % self.delivery_type)(
                pickings, tracking_number, origin_date
            )
            if self.get_return_label_from_portal:
                pickings.return_label_ids.generate_access_token()
            return res
        return None

    def get_return_label_prefix(self):
        return "LabelReturn-%s" % self.delivery_type

    def _get_delivery_label_prefix(self):
        return "LabelShipping-%s" % self.delivery_type

    def _get_delivery_doc_prefix(self):
        return "ShippingDoc-%s" % self.delivery_type

    def get_tracking_link(self, picking):
        self.check_singleton()
        if hasattr(self, "%s_get_tracking_link" % self.delivery_type):
            return getattr(self, "%s_get_tracking_link" % self.delivery_type)(picking)
        return None

    def cancel_shipment(self, pickings):
        _debug.pipeline("carrier_cancel_shipment", carrier=self.id, pickings=pickings)
        self.check_singleton()
        if hasattr(self, "%s_cancel_shipment" % self.delivery_type):
            return getattr(self, "%s_cancel_shipment" % self.delivery_type)(pickings)
        return None

    def _get_default_custom_package_code(self):
        self.check_singleton()
        if hasattr(self, "_%s_get_default_custom_package_code" % self.delivery_type):
            return getattr(
                self, "_%s_get_default_custom_package_code" % self.delivery_type
            )()
        else:
            return False

    def _get_packages_from_order(self, order, default_package_type):
        _debug.perf.count("packages_from_order", carrier=self.id, order=order.id)
        total_cost = 0
        for line in order.line_ids.filtered(
            lambda line: not line.is_delivery and not line.display_type
        ):
            total_cost += self._product_price_to_company_currency(
                line.product_qty, line.product_id, order.company_id
            )

        total_weight = order._get_estimated_weight() + default_package_type.base_weight
        order_weight = self.env.context.get("order_weight", False)
        total_weight = order_weight or total_weight
        if float_is_zero(
            total_weight,
            precision_digits=self.env["decimal.precision"].get_precision(
                "Stock Weight"
            ),
        ):
            weight_uom_name = self.env[
                "product.template"
            ]._get_weight_uom_name_from_ir_config_parameter()
            raise UserError(
                _(
                    "The package cannot be created because the total weight of the products in the picking is 0.0 %s",
                    weight_uom_name,
                )
            )
        max_weight = default_package_type.max_weight or total_weight + 1
        total_full_packages = int(total_weight / max_weight)
        last_package_weight = total_weight % max_weight

        package_weights = [max_weight] * total_full_packages + (
            [last_package_weight] if last_package_weight else []
        )
        num_packages = len(package_weights)
        partial_cost = total_cost / num_packages
        order_commodities = self._get_commodities_from_order(order)

        packages_commodities = [[] for _ in range(num_packages)]
        for commodity in order_commodities:
            base_qty, remainder = divmod(commodity.qty, num_packages)
            monetary_value = commodity.monetary_value / num_packages
            for index in range(num_packages):
                qty = base_qty + (1 if index < remainder else 0)
                if not qty:
                    continue
                packages_commodities[index].append(
                    DeliveryCommodity(
                        commodity.product_id,
                        amount=qty,
                        monetary_value=monetary_value,
                        country_of_origin=commodity.country_of_origin,
                    )
                )

        return [
            DeliveryPackage(
                packages_commodities[index],
                weight,
                default_package_type,
                total_cost=partial_cost,
                currency=order.company_id.currency_id,
                order=order,
            )
            for index, weight in enumerate(package_weights)
        ]

    def _get_packages_from_picking(self, picking, default_package_type):
        _debug.perf.count("packages_from_picking", carrier=self.id, picking=picking.id)
        packages = []

        if picking.is_return_picking:
            commodities = self._get_commodities_from_stock_move_lines(
                picking.move_line_ids
            )
            weight = picking._get_estimated_weight() + default_package_type.base_weight
            packages.append(
                DeliveryPackage(
                    commodities,
                    weight,
                    default_package_type,
                    currency=picking.company_id.currency_id,
                    picking=picking,
                )
            )
            return packages

        for package in picking.move_line_ids.result_package_id:
            move_lines = picking.move_line_ids.filtered(
                lambda ml, package=package: ml.result_package_id == package
            )
            commodities = self._get_commodities_from_stock_move_lines(move_lines)
            package_total_cost = 0.0
            for quant in package.quant_ids:
                package_total_cost += self._product_price_to_company_currency(
                    quant.quantity, quant.product_id, picking.company_id
                )
            packages.append(
                DeliveryPackage(
                    commodities,
                    package.shipping_weight or package.weight,
                    package.package_type_id,
                    name=package.name,
                    total_cost=package_total_cost,
                    currency=picking.company_id.currency_id,
                    picking=picking,
                )
            )

        if picking.weight_bulk:
            commodities = self._get_commodities_from_stock_move_lines(
                picking.move_line_ids
            )
            package_total_cost = 0.0
            for move_line in picking.move_line_ids:
                package_total_cost += self._product_price_to_company_currency(
                    move_line.quantity, move_line.product_id, picking.company_id
                )
            packages.append(
                DeliveryPackage(
                    commodities,
                    picking.weight_bulk,
                    default_package_type,
                    name="Bulk Content",
                    total_cost=package_total_cost,
                    currency=picking.company_id.currency_id,
                    picking=picking,
                )
            )
        elif not packages:
            raise UserError(
                _(
                    "The package cannot be created because the total weight of the "
                    "products in the picking is 0.0 %s",
                    picking.weight_uom_name,
                )
            )
        return packages

    def _get_commodities_from_order(self, order):
        _debug.perf.count("commodities_from_order", carrier=self.id, order=order.id)
        commodities = []

        for line in order.line_ids.filtered(
            lambda line: (
                not line.is_delivery
                and not line.display_type
                and line.product_id.type == "consu"
            )
        ):
            unit_quantity = line.product_uom_id._get_quantity_in_unit(
                line.product_uom_qty, line.product_id.uom_id
            )
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = (
                line.product_id.country_of_origin.code
                or order.warehouse_id.partner_id.country_id.code
            )
            commodities.append(
                DeliveryCommodity(
                    line.product_id,
                    amount=rounded_qty,
                    monetary_value=line.price_unit_discounted_taxinc,
                    country_of_origin=country_of_origin,
                )
            )

        return commodities

    def _get_commodities_from_stock_move_lines(self, move_lines):
        _debug.perf.count("commodities_from_lines", carrier=self.id, lines=move_lines)
        commodities = []

        product_lines = move_lines.filtered(
            lambda line: line.product_id.type == "consu"
        )
        for product, lines in groupby(product_lines, lambda x: x.product_id):
            unit_quantity = sum(
                line.product_uom_id._get_quantity_in_unit(line.quantity, product.uom_id)
                for line in lines
            )
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = (
                product.country_of_origin.code
                or lines[
                    0
                ].picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            )
            unit_price = sum(line.sale_price for line in lines) / rounded_qty
            commodities.append(
                DeliveryCommodity(
                    product,
                    amount=rounded_qty,
                    monetary_value=unit_price,
                    country_of_origin=country_of_origin,
                )
            )

        return commodities

    def _prepare_commodity_values_from_move_lines(self, move_lines):
        commodities = []

        product_lines = move_lines.filtered(
            lambda line: line.product_id.type in ["product", "consu"]
        )
        for product, lines in groupby(product_lines, lambda x: x.product_id):
            unit_quantity = sum(
                line.product_uom_id._get_quantity_in_unit(line.quantity, product.uom_id)
                for line in lines
            )
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = lines[
                0
            ].picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            unit_price = sum(line.sale_price for line in lines) / rounded_qty
            commodities.append(
                {
                    "product_id": product,
                    "qty": rounded_qty,
                    "monetary_value": unit_price,
                    "country_of_origin": country_of_origin,
                }
            )

        return commodities

    def _product_price_to_company_currency(self, quantity, product, company):
        return company.currency_id._convert(
            quantity * product.standard_price,
            product.currency_id,
            company,
            fields.Date.today(),
        )

    def fixed_send_shipping(self, pickings):
        res = []
        for p in pickings:
            res += [{"exact_price": p.carrier_id.fixed_price, "tracking_number": False}]
        return res

    def fixed_get_tracking_link(self, picking):
        if self.tracking_url and picking.carrier_tracking_ref:
            return self.tracking_url.replace(
                "<shipmenttrackingnumber>", picking.carrier_tracking_ref
            )
        return False

    def fixed_cancel_shipment(self, pickings):
        raise NotImplementedError

    def base_on_rule_send_shipping(self, pickings):
        res = []
        for p in pickings:
            carrier = self._match_address(p.partner_id)
            if not carrier:
                raise ValidationError(_("There is no matching delivery rule."))
            res += [
                {
                    "exact_price": p.carrier_id._get_price_available(p.sale_id)
                    if p.sale_id
                    else 0.0,
                    "tracking_number": False,
                }
            ]
        return res

    def base_on_rule_get_tracking_link(self, picking):
        if self.tracking_url and picking.carrier_tracking_ref:
            return self.tracking_url.replace(
                "<shipmenttrackingnumber>", picking.carrier_tracking_ref
            )
        return False

    def base_on_rule_cancel_shipment(self, pickings):
        raise NotImplementedError
