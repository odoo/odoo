from odoo import api, fields, models
from odoo.db.schema import column_exists, create_column
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockRoute(models.Model):
    _inherit = "stock.route"

    shipping_selectable = fields.Boolean(string="Applicable on Shipping Methods")


class StockMove(models.Model):
    _inherit = "stock.move"

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_move", "weight"):
            create_column(self.env.cr, "stock_move", "weight", "numeric")
            self.env.cr.execute("""
                UPDATE stock_move move
                SET weight = move.product_qty * product.weight
                FROM product_product product
                WHERE move.product_id = product.id
                AND move.state != 'cancel'
                """)
        return super()._auto_init()

    weight = fields.Float(
        digits="Stock Weight",
        compute="_compute_weight",
        compute_sudo=True,
        store=True,
    )

    @api.depends("product_id", "product_uom_qty", "product_uom_id")
    def _compute_weight(self):
        _debug.perf.count("move_weight_compute", moves=self)
        moves_with_weight = self.filtered(lambda moves: moves.product_id.weight > 0.00)
        for move in moves_with_weight:
            move.weight = move.product_qty * move.product_id.weight
        (self - moves_with_weight).weight = 0

    def _prepare_new_picking_vals(self):
        vals = super()._prepare_new_picking_vals()
        if not any(rule.propagate_carrier for rule in self.rule_id):
            return vals
        carrier_id = (
            len(self.reference_ids.sale_ids.carrier_id) == 1
            and self.reference_ids.sale_ids.carrier_id.id
        )
        carrier_tracking_ref = self.move_orig_ids.picking_id.filtered(
            "carrier_tracking_ref"
        )[:1].carrier_tracking_ref
        if len(self.move_orig_ids.picking_id.carrier_id) == 1:
            carrier_id = self.move_orig_ids.picking_id.carrier_id.id
        if carrier_id:
            vals["carrier_id"] = carrier_id
        if carrier_tracking_ref:
            vals["carrier_tracking_ref"] = carrier_tracking_ref
        return vals

    def _get_picking_assignation_key(self):
        keys = super()._get_picking_assignation_key()
        return keys + (self.sale_line_id.order_id.carrier_id,)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sale_price = fields.Float(compute="_compute_sale_price")
    destination_country_code = fields.Char(
        related="picking_id.destination_country_code"
    )
    carrier_id = fields.Many2one(related="picking_id.carrier_id")

    @api.depends(
        "quantity",
        "product_uom_id",
        "product_id",
        "move_id.sale_line_id",
        "move_id.sale_line_id.price_unit_discounted_taxinc",
        "move_id.sale_line_id.product_uom_id",
    )
    def _compute_sale_price(self):
        for move_line in self:
            sale_line_id = move_line.move_id.sale_line_id
            if sale_line_id and sale_line_id.product_id == move_line.product_id:
                base_line = sale_line_id._prepare_base_line_for_taxes_computation()
                qty = move_line.product_uom_id._get_quantity_in_unit(
                    move_line.quantity, sale_line_id.product_uom_id
                )
                base_line.update({"quantity": qty})
                self.env["account.tax"]._add_tax_details_in_base_line(
                    base_line, sale_line_id.company_id
                )
                tax_results = base_line["tax_details"]
                move_line.sale_price = sale_line_id.currency_id.round(
                    tax_results["raw_total_included_currency"]
                )
            else:
                unit_price = move_line.product_id.list_price
                qty = move_line.product_uom_id._get_quantity_in_unit(
                    move_line.quantity, move_line.product_id.uom_id
                )
                move_line.sale_price = unit_price * qty
        super()._compute_sale_price()

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        for aggregated_move_line in aggregated_move_lines:
            hs_code = aggregated_move_lines[aggregated_move_line][
                "product"
            ].product_tmpl_id.hs_code
            aggregated_move_lines[aggregated_move_line]["hs_code"] = hs_code
        return aggregated_move_lines

    def _pre_put_in_pack_hook(
        self,
        all_lines=False,
        package_id=False,
        package_type_id=False,
        package_name=False,
        from_package_wizard=False,
    ):
        _debug.pipeline("put_in_pack_pre", lines=self)
        res = super()._pre_put_in_pack_hook(
            all_lines, package_id, package_type_id, package_name, from_package_wizard
        )
        if res and not from_package_wizard and self.carrier_id:
            context = res.get("context", {})
            context["default_package_carrier_type"] = (
                self._get_package_carrier_type_for_pack()
            )
            res["context"] = context
        return res

    def _post_put_in_pack_hook(self, package):
        _debug.pipeline("put_in_pack_post", lines=self, package=package.id)
        weight = self.env.context.get("weight")
        if weight:
            package.shipping_weight = weight
        return super()._post_put_in_pack_hook(package)

    def _get_package_carrier_type_for_pack(self):
        if len(self.carrier_id) > 1 or any(not ml.carrier_id for ml in self):
            raise UserError(
                self.env._(
                    "You cannot pack products into the same package when they have different carriers (i.e. check that all of their transfers have a carrier assigned and are using the same carrier)."
                )
            )

        package_carrier_type = self.carrier_id.delivery_type
        if package_carrier_type in ["fixed", "base_on_rule"]:
            package_carrier_type = "none"
        return package_carrier_type

    def _is_package_set_required(self):
        _debug.logic("package_set_required_check", lines=self)
        if self.carrier_id:
            return True
        return super()._is_package_set_required()
