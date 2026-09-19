from collections import defaultdict
from datetime import UTC
from itertools import groupby
from uuid import uuid4

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_compare, float_is_zero

from ..tools import debug_log as dbg


class PosOrderLine(models.Model):
    _name = "pos.order.line"
    _description = "Point of Sale Order Lines"
    _rec_name = "product_id"
    _inherit = ["mixin.pos.load"]

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="order_id.company_id",
        string="Company",
    )
    name = fields.Char(
        string="Line No",
        copy=False,
        required=True,
    )
    notice = fields.Char(string="Discount Notice")
    product_id = fields.Many2one(
        comodel_name="product.product",
        change_default=True,
        required=True,
        domain=[("sale_ok", "=", True)],
    )
    attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        string="Selected Attributes",
    )
    custom_attribute_value_ids = fields.One2many(
        comodel_name="product.attribute.custom.value",
        inverse_name="pos_order_line_id",
        string="Custom Values",
        store=True,
        readonly=False,
    )
    price_unit = fields.Float(
        string="Unit Price",
        digits=0,
    )
    qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        default=1,
    )
    price_subtotal = fields.Monetary(
        string="Tax Excl.",
        readonly=True,
        required=True,
        help="Signed like `qty`, as `total_cost` and `amount_total` are.",
    )
    price_subtotal_incl = fields.Monetary(
        string="Tax Incl.",
        readonly=True,
        required=True,
        help="Signed like `qty`, as `price_subtotal` is.",
    )
    price_extra = fields.Float(string="Price extra")
    price_type = fields.Selection(
        selection=[
            ("original", "Original"),
            ("manual", "Manual"),
            ("automatic", "Automatic"),
        ],
        default="original",
    )
    margin = fields.Monetary(
        compute="_compute_margins",
        store=True,
    )
    margin_percent = fields.Float(
        string="Margin (%)",
        digits=(12, 4),
        compute="_compute_margins",
        store=True,
    )
    total_cost = fields.Float(
        string="Total cost",
        min_display_digits="Product Price",
        readonly=True,
    )
    price_cost = fields.Float(
        string="Cost",
        readonly=True,
        help="Unit cost behind `total_cost`, which stores `qty * cost` converted "
        "to the line currency. Reporting needs the two separately.",
    )
    is_total_cost_computed = fields.Boolean(
        help="Allows to know if the total cost has already been computed or not"
    )
    discount = fields.Float(
        string="Discount (%)",
        digits=0,
        default=0.0,
    )
    order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Order Ref",
        index=True,
        required=True,
        ondelete="cascade",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        readonly=True,
    )
    tax_ids_after_fiscal_position = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes to Apply",
        compute="_compute_tax_ids_after_fiscal_position",
    )
    pack_lot_ids = fields.One2many(
        comodel_name="pos.pack.operation.lot",
        inverse_name="pos_order_line_id",
        string="Lot/serial Number",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
        string="Product Unit",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="order_id.currency_id",
    )
    full_product_name = fields.Char()
    customer_note = fields.Char()
    refund_orderline_ids = fields.One2many(
        comodel_name="pos.order.line",
        inverse_name="refunded_orderline_id",
        string="Refund Order Lines",
        help="Orderlines in this field are the lines that refunded this orderline.",
    )
    refunded_orderline_id = fields.Many2one(
        comodel_name="pos.order.line",
        string="Refunded Order Line",
        index="btree_not_null",
        help="If this orderline is a refund, then the refunded orderline is specified in this field.",
    )
    refunded_qty = fields.Float(
        string="Refunded Quantity",
        compute="_compute_refunded_qty",
        help="Number of items refunded in this orderline.",
    )
    uuid = fields.Char(
        default=lambda self: str(uuid4()),
        copy=False,
        readonly=True,
    )
    note = fields.Char(string="Product Note")

    combo_parent_id = fields.Many2one(
        comodel_name="pos.order.line",
        index="btree_not_null",
    )
    combo_line_ids = fields.One2many(
        comodel_name="pos.order.line",
        inverse_name="combo_parent_id",
        string="Combo Lines",
    )

    combo_item_id = fields.Many2one(comodel_name="product.combo.item")
    is_edited = fields.Boolean(
        string="Edited",
        default=False,
    )
    extra_tax_data = fields.Json()

    _unique_uuid = models.Constraint(
        "unique (uuid)", "An order line with this uuid already exists"
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [
            ("order_id", "in", [order["id"] for order in data["pos.order"]]),
            ("product_id.active", "=", True),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "qty",
            "attribute_value_ids",
            "custom_attribute_value_ids",
            "price_unit",
            "uuid",
            "price_subtotal",
            "price_subtotal_incl",
            "order_id",
            "note",
            "price_type",
            "product_id",
            "discount",
            "tax_ids",
            "pack_lot_ids",
            "customer_note",
            "refunded_qty",
            "price_extra",
            "full_product_name",
            "refunded_orderline_id",
            "combo_parent_id",
            "combo_line_ids",
            "combo_item_id",
            "refund_orderline_ids",
            "extra_tax_data",
            "write_date",
        ]

    @api.model
    def _is_field_accepted(self, field_name):
        return field_name in self._fields and field_name not in [
            "combo_parent_id",
            "combo_line_ids",
        ]

    @api.depends(
        "refund_orderline_ids",
        "refund_orderline_ids.qty",
        "refund_orderline_ids.order_id.state",
    )
    def _compute_refunded_qty(self):
        for orderline in self:
            refund_order_line = orderline.refund_orderline_ids.filtered(
                lambda l: l.order_id.state != "cancel"
            )
            orderline.refunded_qty = -sum(refund_order_line.mapped("qty"))

    def _get_refundable_lines(self):
        digits = self.env["decimal.precision"].get_precision("Product Unit")
        return self.filtered(
            lambda line: (
                float_compare(line.qty, line.refunded_qty, precision_digits=digits) > 0
            )
        )

    def _prepare_refund_data(self, refund_order, refund_lots):
        self.check_singleton()
        return {
            "name": _("%(name)s REFUND", name=self.name),
            "qty": -(self.qty - self.refunded_qty),
            "order_id": refund_order.id,
            "pack_lot_ids": refund_lots,
            "is_total_cost_computed": False,
            "refunded_orderline_id": self.id,
        }

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        unnamed = [vals for vals in vals_list if not vals.get("name")]
        dbg.lifecycle.debug(
            "pos.order.line.create: %d vals (%d unnamed), keys=%s",
            len(vals_list),
            len(unnamed),
            dbg.vals_keys(vals_list),
        )
        if unnamed:
            PosOrder = self.env["pos.order"]
            orders = PosOrder.browse(
                [vals["order_id"] for vals in unnamed if vals.get("order_id")]
            ).exists()
            sequence_by_order_id = {
                order.id: order.session_id.config_id.order_line_seq_id
                for order in orders
            }
            order_by_id = {order.id: order for order in orders}
            for vals in unnamed:
                order_id = vals.get("order_id")
                order = order_by_id.get(order_id, PosOrder)
                sequence = sequence_by_order_id.get(order_id, self.env["ir.sequence"])
                if not sequence:
                    raise UserError(
                        _(
                            "The point of sale %(config)s has no order-line"
                            " sequence, so its order lines cannot be numbered.",
                            config=order.session_id.config_id.display_name
                            or order.display_name,
                        )
                    )
                vals["name"] = sequence.sudo()._next()
        return super().create(vals_list)

    def write(self, vals):
        new_qty = vals.get("qty")
        dbg.lifecycle.debug(
            "pos.order.line.write: %s keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if new_qty is not None:
            digits = self.env["decimal.precision"].get_precision("Product Unit")
            edited = self.browse()
            bodies_per_order = defaultdict(list)
            for line in self:
                if not line.order_id.config_id.order_edit_tracking:
                    continue
                if float_compare(new_qty, line.qty, digits) >= 0:
                    continue
                dbg.logic.debug(
                    "[order:%s] line %s qty %s -> %s tracked as edit",
                    line.order_id.uuid,
                    line.id,
                    line.qty,
                    new_qty,
                )
                edited |= line
                body = _(
                    "%(product_name)s: Ordered quantity: %(old_qty)s",
                    product_name=line.full_product_name,
                    old_qty=line.qty,
                )
                bodies_per_order[line.order_id].append(
                    body + Markup("&rarr;") + str(new_qty)
                )
            for order, bodies in bodies_per_order.items():
                body = (
                    bodies[0]
                    if len(bodies) == 1
                    else order._markup_list_message(bodies)
                )
                order.message_post(body=order._prepare_pos_log(body))
            edited.is_edited = True
        return super().write(vals)

    @api.model
    def get_existing_lots(self, company_id, config_id, product_id):
        self.check_access("read")
        pos_config = self.env["pos.config"].browse(config_id)
        if not pos_config:
            raise UserError(_("No PoS configuration found"))

        company_id = pos_config.company_id.id
        src_loc = pos_config.picking_type_id.default_location_src_id

        domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company_id),
            ("product_id", "=", product_id),
            ("location_id", "in", src_loc.child_internal_location_ids.ids),
            ("quantity", ">", 0),
            ("lot_id", "!=", False),
        ]

        groups = (
            self.sudo()
            .env["stock.quant"]
            ._read_group(domain=domain, groupby=["lot_id"], aggregates=["quantity:sum"])
        )

        result = []
        for lot_recordset, total_quantity in groups:
            if lot_recordset:
                result.append(
                    {
                        "id": lot_recordset.id,
                        "name": lot_recordset.name,
                        "product_qty": total_quantity,
                    }
                )

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_order_state(self):
        if self.filtered(lambda x: x.order_id.state not in ["draft", "cancel"]):
            raise UserError(
                _(
                    "You can only unlink PoS order lines that are related to orders in new or cancelled state."
                )
            )

    @api.onchange("price_unit", "tax_ids", "qty", "discount", "product_id")
    def _onchange_amount_line_all(self):
        for line in self:
            res = line._get_amount_line_all()
            line.update(res)

    def _get_amount_line_all(self):
        self.check_singleton()
        fpos = self.order_id.fiscal_position_id
        tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids)
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = tax_ids_after_fiscal_position.compute_all(
            price,
            self.order_id.currency_id,
            self.qty,
            product=self.product_id,
            partner=self.order_id.partner_id,
        )
        return {
            "price_subtotal_incl": taxes["total_included"],
            "price_subtotal": taxes["total_excluded"],
        }

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            price = self.order_id.pricelist_id._get_product_price(
                self.product_id, self.qty or 1.0, currency=self.currency_id
            )
            self.tax_ids = self.product_id.taxes_id.filtered_domain(
                self.env["account.tax"]._check_company_domain(self.company_id)
            )
            tax_ids_after_fiscal_position = self.order_id.fiscal_position_id.map_tax(
                self.tax_ids
            )
            self.price_unit = self.env["account.tax"]._fix_tax_included_price_company(
                price, self.tax_ids, tax_ids_after_fiscal_position, self.company_id
            )
            self._onchange_amount_line_all()

    @api.depends("order_id", "order_id.fiscal_position_id", "tax_ids")
    def _compute_tax_ids_after_fiscal_position(self):
        for line in self:
            line.tax_ids_after_fiscal_position = (
                line.order_id.fiscal_position_id.map_tax(line.tax_ids)
            )

    def _prepare_reference_vals(self):
        return {
            "name": self.order_id.name,
            "pos_order_ids": [Command.link(self.order_id.id)],
        }

    def _prepare_procurement_vals(self):
        self.check_singleton()
        if self.order_id.shipping_date:
            from_zone = self.env.tz
            shipping_date = fields.Datetime.to_datetime(self.order_id.shipping_date)
            shipping_date = shipping_date.replace(tzinfo=from_zone)
            date_deadline = shipping_date.astimezone(UTC).replace(tzinfo=None)
        else:
            date_deadline = self.order_id.date_order

        return {
            "date_planned": date_deadline,
            "date_deadline": date_deadline,
            "route_ids": self.order_id.config_id.route_id,
            "warehouse_id": self.order_id.config_id.warehouse_id or False,
            "partner_id": self.order_id.partner_id.id,
            "product_description_variants": self.full_product_name,
            "company_id": self.order_id.company_id,
            "reference_ids": self.order_id.reference_ids,
        }

    @dbg.timed
    def _launch_stock_rule_from_pos_order_lines(self):

        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.product_id.type != "consu":
                dbg.logic.debug(
                    "[order:%s] line %s skipped: product type %s",
                    line.order_id.uuid,
                    line.id,
                    line.product_id.type,
                )
                continue

            reference_ids = line.order_id.reference_ids
            if not reference_ids:
                reference_ids = (
                    self.env["stock.reference"]
                    .sudo()
                    .create(line._prepare_reference_vals())
                )
                line.order_id.reference_ids = [Command.set(reference_ids.ids)]
                dbg.pipeline.debug(
                    "[order:%s] stock.reference %s created",
                    line.order_id.uuid,
                    dbg.rec(reference_ids),
                )

            values = line._prepare_procurement_vals()
            product_qty = line.qty

            procurement_uom = line.product_id.uom_id
            procurements.append(
                self.env["stock.rule"].Procurement(
                    line.product_id,
                    product_qty,
                    procurement_uom,
                    line.order_id.partner_id.property_stock_customer,
                    line.name,
                    line.order_id.name,
                    line.order_id.company_id,
                    values,
                )
            )
        dbg.pipeline.debug(
            "procurements: %d for %s", len(procurements), dbg.rec(self.order_id)
        )
        if procurements:
            with dbg.timer(self.env, "stock.rule.run for %s", dbg.rec(self.order_id)):
                self.env["stock.rule"].run(procurements)

        orders = self.mapped("order_id")
        for order in orders:
            pickings_to_confirm = order.picking_ids
            dbg.pipeline.debug(
                "[order:%s] pickings to confirm: %s",
                order.uuid,
                dbg.rec(pickings_to_confirm),
            )
            if pickings_to_confirm:
                tracked_lines = order.lines.filtered(
                    lambda l: l.product_id.tracking != "none"
                )
                lines_by_tracked_product = groupby(
                    sorted(tracked_lines, key=lambda l: l.product_id.id),
                    key=lambda l: l.product_id.id,
                )
                pickings_to_confirm.action_confirm()
                for product_id, lines in lines_by_tracked_product:
                    lines = self.env["pos.order.line"].concat(*lines)
                    moves = pickings_to_confirm.move_ids.filtered(
                        lambda m, product_id=product_id: m.product_id.id == product_id
                    )
                    moves.move_line_ids.unlink()
                    moves._add_move_lines_from_pos_order_lines(
                        lines, are_quantities_done=False
                    )
                    moves._recompute_state()
        return True

    def _is_product_storable_fifo_avco(self):
        self.check_singleton()
        return self.product_id.is_storable and self.product_id.cost_method in [
            "fifo",
            "average",
        ]

    def _get_product_cost_with_moves(self, moves):
        self.check_singleton()
        return moves._get_price_unit()

    @dbg.timed
    def _update_total_cost(self, stock_moves):
        for line in self.filtered(lambda l: not l.is_total_cost_computed):
            line = line.with_company(line.company_id)
            product = line.product_id
            cost_currency = product.sudo().cost_currency_id
            moves = (
                line._get_stock_moves_to_consider(stock_moves, product)
                if stock_moves
                else None
            )
            if moves and line._is_product_storable_fifo_avco():
                product_cost = line._get_product_cost_with_moves(moves)
                source = "moves"
                if cost_currency.is_zero(product_cost) and line.order_id.shipping_date:
                    refunded = line.refunded_orderline_id
                    if refunded and refunded.qty:
                        # Keep the recorded source cost even if historical rates
                        # were corrected. Older lines may lack that unit cost.
                        product_cost = (
                            refunded.price_cost
                            or refunded.currency_id._convert(
                                refunded.total_cost / refunded.qty,
                                cost_currency,
                                refunded.company_id,
                                refunded.order_id.date_order,
                                round=False,
                            )
                        )
                        source = "refunded line"
                    else:
                        product_cost = product.standard_price
                        source = "standard_price (zero move cost)"
            else:
                product_cost = product.standard_price
                source = "standard_price"
            dbg.logic.debug(
                "[order:%s] line %s cost %s from %s (moves=%s)",
                line.order_id.uuid,
                line.id,
                product_cost,
                source,
                dbg.rec(moves) if moves else None,
            )
            line.total_cost = line.qty * cost_currency._convert(
                from_amount=product_cost,
                to_currency=line.currency_id,
                company=line.company_id or self.env.company,
                date=line.order_id.date_order or fields.Date.today(),
                round=False,
            )
            line.price_cost = product_cost
            line.is_total_cost_computed = True

    def _get_stock_moves_to_consider(self, stock_moves, product):
        self.check_singleton()
        return stock_moves.filtered(lambda ml: ml.product_id.id == product.id)

    @api.depends("price_subtotal", "total_cost")
    def _compute_margins(self):
        for line in self:
            if line.product_id.type == "combo":
                line.margin = 0
                line.margin_percent = 0
            else:
                line.margin = line.price_subtotal - line.total_cost
                line.margin_percent = (
                    not float_is_zero(
                        line.price_subtotal,
                        precision_rounding=line.currency_id.rounding,
                    )
                    and line.margin / line.price_subtotal
                ) or 0

    def _prepare_base_line_for_taxes_computation(self):
        self.check_singleton()
        commercial_partner = self.order_id.partner_id.commercial_partner_id
        fiscal_position = self.order_id.fiscal_position_id
        line = self.with_company(self.order_id.company_id)
        account = (
            line.product_id._get_product_accounts()["income"]
            or self.order_id.config_id.journal_id.default_account_id
        )
        if not account:
            raise UserError(
                _(
                    "Please define income account for this product: '%(product)s' (id:%(id)d).",
                    product=line.product_id.name,
                    id=line.product_id.id,
                )
            )

        if fiscal_position:
            account = fiscal_position.map_account(account)

        is_refund_order = line.order_id._is_refund_order()
        is_refund_line = line.qty * line.price_unit < 0

        lang = line.order_id.partner_id.lang or self.env.user.lang
        product_name = (
            line.with_context(lang=lang).full_product_name
            or line.product_id.with_context(lang=lang).display_name
        )
        if line.product_id.description_sale:
            product_name += (
                "\n" + line.product_id.with_context(lang=lang).description_sale
            )
        return {
            **self.env["account.tax"]._prepare_base_line_for_taxes_computation(
                line,
                partner_id=commercial_partner,
                currency_id=self.order_id.currency_id,
                rate=self.order_id.currency_rate,
                product_id=line.product_id,
                tax_ids=line.tax_ids_after_fiscal_position,
                price_unit=line.price_unit,
                quantity=line.qty * (-1 if is_refund_order else 1),
                discount=line.discount,
                account_id=account,
                is_refund=is_refund_line,
                sign=1 if is_refund_order else -1,
            ),
            "uom_id": line.product_uom_id,
            "name": product_name,
        }

    def _prepare_tax_base_line_values(self):
        return [line._prepare_base_line_for_taxes_computation() for line in self]

    def unlink(self):
        dbg.lifecycle.debug("pos.order.line.unlink: %s", dbg.rec(self))
        bodies_per_order = defaultdict(list)
        for line in self:
            if line.order_id.config_id.order_edit_tracking:
                bodies_per_order[line.order_id].append(
                    _(
                        "%(product_name)s: Deleted line (quantity: %(qty)s)",
                        product_name=line.full_product_name,
                        qty=line.qty,
                    )
                )
        for order, bodies in bodies_per_order.items():
            order.has_deleted_line = True
            body = bodies[0] if len(bodies) == 1 else order._markup_list_message(bodies)
            order.message_post(body=order._prepare_pos_log(body))
        return super().unlink()

    def _get_discount_amount(self):
        self.check_singleton()
        original_price = self.tax_ids_after_fiscal_position.compute_all(
            self.price_unit,
            self.currency_id,
            self.qty,
            product=self.product_id,
            partner=self.order_id.partner_id,
        )["total_included"]
        return original_price - self.price_subtotal_incl
