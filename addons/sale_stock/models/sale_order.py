import json
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "mixin.order.stock"]

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        compute="_compute_warehouse_id",
        precompute=True,
        store=True,
        readonly=False,
        check_company=True,
    )
    picking_policy = fields.Selection(
        selection=[
            ("direct", "As soon as possible"),
            ("one", "When all products are ready"),
        ],
        string="Shipping Policy",
        default="direct",
        required=True,
        help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.",
    )
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="sale_id",
        string="Transfers",
    )
    count_transfer_outgoing = fields.Integer(
        string="Delivery Orders",
        compute="_compute_outgoing_transfer_counts",
    )
    reference_ids = fields.Many2many(
        comodel_name="stock.reference",
        relation="stock_reference_sale_rel",
        column1="sale_id",
        column2="reference_id",
        string="References",
        copy=False,
    )
    transfer_state = fields.Selection(
        string="Delivery Status",
        help="Blue: Not Delivered/Started\n\
            Orange: Partially transferred\n\
            Green: Fully transferred",
    )
    late_availability = fields.Boolean(
        compute="_compute_late_availability",
        search="_search_late_availability",
        help="True if any related picking has late availability",
    )
    date_planned = fields.Datetime(
        help="Delivery date you can promise to the customer, computed from the minimum lead time of "
        "the order lines in case of Service products. In case of shipping, the shipping policy of "
        "the order will be taken into account to either use the minimum or maximum lead time of "
        "the order lines."
    )
    date_effective = fields.Datetime(
        string="Effective Date",
        help="Completion date of the first delivery order.",
    )
    json_popover = fields.Char(
        string="JSON data for the popover widget",
        compute="_compute_popover",
    )
    show_json_popover = fields.Boolean(
        string="Has late picking",
        compute="_compute_popover",
    )

    def _init_column(self, column_name, *, new_column=False):
        if column_name != "warehouse_id":
            return super()._init_column(column_name, new_column=new_column)

        default_warehouse = self.env["stock.warehouse"].search([], limit=1)

        query = """
        UPDATE sale_order so
        SET warehouse_id = COALESCE(wh.id, %s)
        FROM stock_warehouse wh
        WHERE so.company_id = wh.company_id and so.warehouse_id IS NULL and wh.active
        """
        params = [default_warehouse.id]

        _logger.debug(
            "Initializing column '%s' in table '%s'",
            column_name,
            self._table,
        )
        self.env.cr.execute(query, params)
        return None

    @api.constrains("warehouse_id", "state", "line_ids")
    def _check_warehouse(self):
        orders_without_wh = self.filtered(
            lambda order: (
                order.state not in ("draft", "cancel") and not order.warehouse_id
            ),
        )
        company_ids_with_wh = {
            company_id.id
            for [company_id] in self.env["stock.warehouse"]._read_group(
                domain=[("company_id", "in", orders_without_wh.company_id.ids)],
                groupby=["company_id"],
            )
        }
        other_company = set()
        for order_line in orders_without_wh.line_ids:
            if order_line.product_id.type != "consu":
                continue
            if (
                order_line.route_ids.company_id
                and order_line.route_ids.company_id != order_line.company_id
            ):
                other_company.add(order_line.route_ids.company_id.id)
                continue
            if order_line.order_id.company_id.id in company_ids_with_wh:
                _debug.logic(
                    "warehouse_required",
                    order=order_line.order_id,
                    company=order_line.order_id.company_id,
                )
                raise ValidationError(
                    _("You must set a warehouse on your sale order to proceed."),
                )
            self.env["stock.warehouse"].with_company(
                order_line.order_id.company_id,
            )._raise_missing_warehouse()
        other_company_warehouses = self.env["stock.warehouse"].search(
            [("company_id", "in", list(other_company))],
        )
        if any(c not in other_company_warehouses.company_id.ids for c in other_company):
            _debug.logic(
                "cross_company_warehouse_missing",
                orders=orders_without_wh,
                companies=len(other_company),
            )
            raise ValidationError(
                _(
                    "You must have a warehouse for line using a delivery in different company.",
                ),
            )

    def write(self, vals):
        confirmed = (
            self.filtered(lambda o: o.state == "done")
            if vals.get("line_ids")
            else self.browse()
        )
        pre_order_line_qty = {
            order: {
                order_line: order_line.product_qty
                for order_line in order.line_ids
                if not order_line.is_expense
            }
            for order in confirmed
        }

        if vals.get("partner_shipping_id") and self.env.context.get(
            "update_delivery_shipping_partner",
        ):
            for order in self:
                _debug.lifecycle(
                    "picking_partner_realigned", order=order, pickings=order.picking_ids
                )
                order.picking_ids.partner_id = vals.get("partner_shipping_id")
        elif vals.get("partner_shipping_id"):
            new_partner = self.env["res.partner"].browse(
                vals.get("partner_shipping_id"),
            )
            for record in self:
                picking = record.mapped("picking_ids").filtered(
                    lambda x: x.state not in ("done", "cancel"),
                )
                message = _(
                    """
                    The delivery address has been changed on the Sales Order<br/>
                    From <strong>"%(old_address)s"</strong> to <strong>"%(new_address)s"</strong>,
                    You should probably update the partner on this document.
                    """,
                    old_address=record.partner_shipping_id.display_name,
                    new_address=new_partner.display_name,
                )
                _debug.lifecycle(
                    "picking_partner_change_flagged", order=record, pickings=picking
                )
                picking.activity_schedule(
                    "mail.mail_activity_data_warning",
                    note=message,
                    user_id=self.env.user.id,
                )

        if "date_commitment" in vals:
            deadline_datetime = vals.get("date_commitment")
            for order in self:
                moves = order.line_ids.move_ids.filtered(
                    lambda m: (
                        m.state not in ("done", "cancel")
                        and m.location_dest_id.usage == "customer"
                    ),
                )
                _debug.lifecycle("move_deadlines_realigned", order=order, moves=moves)
                moves.date_deadline = deadline_datetime or order.date_planned

        res = super().write(vals)

        confirmed.line_ids.fetch(
            [
                "product_uom_id",
                "product_qty",
                "display_type",
                "is_downpayment",
            ],
        )
        for order in confirmed:
            previous_qty = pre_order_line_qty[order]
            to_log = {}
            for order_line in order.line_ids:
                if order_line.display_type or order_line.is_downpayment:
                    continue
                if (
                    float_compare(
                        order_line.product_qty,
                        previous_qty.get(order_line, 0.0),
                        precision_rounding=order_line.product_uom_id.rounding,
                    )
                    < 0
                ):
                    to_log[order_line] = (
                        order_line.product_qty,
                        previous_qty.get(order_line, 0.0),
                    )
            if to_log:
                documents = (
                    self.env["mixin.stock.activity"]
                    .sudo()
                    ._get_log_activity_documents(
                        to_log,
                        "move_ids",
                        "UP",
                    )
                )
                documents = {
                    k: v for k, v in documents.items() if k[0].state != "cancel"
                }
                _debug.pipeline(
                    "ordered_quantity_decreased", order=order, lines=len(to_log)
                )
                order._log_decrease_ordered_quantity(documents)

        return res

    @api.depends("picking_ids.date_delay_alert")
    def _compute_popover(self):
        for order in self:
            late_stock_picking = order.picking_ids.filtered(
                lambda p: p.date_delay_alert,
            )
            order.json_popover = json.dumps(
                {
                    "popoverTemplate": "sale_stock.DelayAlertWidget",
                    "late_elements": [
                        {
                            "id": late_move.id,
                            "name": late_move.display_name,
                            "model": "stock.picking",
                        }
                        for late_move in late_stock_picking
                    ],
                },
            )
            order.show_json_popover = bool(late_stock_picking)

    @api.depends("company_id", "user_id")
    def _compute_warehouse_id(self):
        for order in self:
            if order.state == "draft" or not order.ids:
                default_warehouse_id = (
                    self.env["ir.default"]
                    .with_company(order.company_id)
                    ._get_model_defaults("sale.order")
                    .get("warehouse_id")
                )
                if default_warehouse_id is not None:
                    order.warehouse_id = default_warehouse_id
                    _debug.logic("warehouse_resolved", order=order, by="ir_default")
                else:
                    order.warehouse_id = order.user_id.with_company(
                        order.company_id,
                    )._get_default_warehouse_id()
                    _debug.logic("warehouse_resolved", order=order, by="user_default")

    @api.depends("picking_policy")
    def _compute_date_planned(self):
        super()._compute_date_planned()

    @api.depends("picking_ids")
    def _compute_outgoing_transfer_counts(self):
        for order in self:
            order.count_transfer_outgoing = len(order.picking_ids)

    def _get_effective_pickings(self, pickings):
        return pickings.filtered(
            lambda p: p.state == "done" and p.location_dest_id.usage == "customer",
        )

    @api.depends("picking_ids.products_availability_state")
    def _compute_late_availability(self):
        for order in self:
            order.late_availability = any(
                picking.products_availability_state == "late"
                for picking in order.picking_ids
            )

    def _search_late_availability(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented

        late_pickings = self.env["stock.picking"]._search(
            [
                ("sale_id", "!=", False),
                ("products_availability_state", "=", "late"),
            ],
        )
        wanted = operator == "=" if value else operator != "="
        return [("picking_ids", "in" if wanted else "not in", late_pickings)]

    @api.onchange("partner_shipping_id")
    def _onchange_partner_shipping_id(self):
        res = {}
        pickings = self.picking_ids.filtered(
            lambda p: (
                p.state not in ["done", "cancel"]
                and p.partner_id != self.partner_shipping_id
            ),
        )
        if pickings:
            _debug.logic(
                "shipping_partner_change_warning",
                order=self._origin,
                pickings=pickings,
            )
            res["warning"] = {
                "title": _("Warning!"),
                "message": _(
                    "Do not forget to change the partner on the following delivery orders: %s",
                    ",".join(pickings.mapped("name")),
                ),
            }
        return res

    def _action_cancel(self):
        lines_quantities = {
            order_line: (order_line.product_qty, 0)
            for sale_order in self
            if sale_order.state == "done"
            for order_line in sale_order.line_ids
        }
        documents = (
            self.env["mixin.stock.activity"]
            .with_context(include_draft_documents=True)
            ._get_log_activity_documents(
                lines_quantities,
                "move_ids",
                "UP",
            )
            if lines_quantities
            else None
        )

        _debug.lifecycle(
            "order_pickings_cancelled", orders=self, pickings=self.picking_ids
        )
        self.picking_ids.filtered(lambda p: p.state != "done").with_context(
            skip_cancel_activity=True
        ).action_cancel()

        if documents:
            filtered_documents = {}

            for (parent, responsible), rendering_context in documents.items():
                if parent._name == "stock.picking":
                    if parent.state == "cancel":
                        continue
                filtered_documents[(parent, responsible)] = rendering_context

            _debug.pipeline(
                "cancel_quantity_exceptions_logged",
                orders=self,
                documents=len(filtered_documents),
            )
            self._log_decrease_ordered_quantity(filtered_documents, cancel=True)

        return super()._action_cancel()

    def _prepare_catalog_extra_context(self):
        return {
            **super()._prepare_catalog_extra_context(),
            "warehouse_id": self.warehouse_id.id,
        }

    def _action_confirm(self):
        _debug.pipeline("launch_stock_rules", orders=self, lines=self.line_ids)
        self.line_ids._action_launch_stock_rule()
        return super()._action_confirm()

    def action_view_picking(self):
        return self._get_action_view_picking(self.picking_ids)

    def _add_reference(self, reference):
        self.check_singleton()
        self.reference_ids = [
            Command.link(stock_reference.id) for stock_reference in reference
        ]

    def _prepare_picking_action_context(self, pickings):
        picking = (
            pickings.filtered(lambda p: p.picking_type_id.code == "outgoing")[:1]
            or pickings[:1]
        )
        return {
            "default_partner_id": self.partner_id.id,
            "default_picking_type_id": picking.picking_type_id.id,
        }

    def _get_date_planned(self, date_planneds):
        _debug.logic("date_planned_policy", order=self, policy=self.picking_policy)
        if self.picking_policy == "direct":
            return super()._get_date_planned(date_planneds)
        return max(date_planneds)

    def _log_decrease_ordered_quantity(self, documents, cancel=False):

        def _render_note_exception_quantity_so(rendering_context):
            order_exceptions, visited_moves = rendering_context
            visited_moves = list(visited_moves)
            visited_moves = self.env[visited_moves[0]._name].concat(*visited_moves)
            line_exceptions = {}
            for order_line, changes in order_exceptions.values():
                line_exceptions.setdefault(order_line, changes)
            order_line_ids = self.env["sale.order.line"].browse(
                [order_line.id for order_line in line_exceptions],
            )
            sale_order_ids = order_line_ids.mapped("order_id")
            impacted_pickings = visited_moves.filtered(
                lambda m: m.state not in ("done", "cancel"),
            ).mapped("picking_id")
            values = {
                "sale_order_ids": sale_order_ids,
                "order_exceptions": list(line_exceptions.items()),
                "impacted_pickings": impacted_pickings,
                "cancel": cancel,
            }
            return self.env["ir.qweb"]._render("sale_stock.exception_on_so", values)

        _debug.pipeline(
            "quantity_exception_activities",
            orders=self,
            documents=len(documents),
            cancel=cancel,
        )
        self.env["mixin.stock.activity"]._log_activity(
            _render_note_exception_quantity_so,
            documents,
        )

    def _prepare_invoice_vals(self):
        invoice_vals = super()._prepare_invoice_vals()
        invoice_vals["invoice_incoterm_id"] = self.incoterm_id.id
        invoice_vals["delivery_date"] = self.date_effective and (
            fields.Datetime.context_timestamp(self, self.date_effective)
        )
        return invoice_vals

    def _remove_reference(self, reference):
        self.check_singleton()
        self.reference_ids = [
            Command.unlink(stock_reference.id) for stock_reference in reference
        ]

    def _is_display_stock_in_catalog(self):
        return True

    def action_delivery_matching(self):
        self.check_singleton()
        return {
            "name": _("Delivery Matching"),
            "type": "ir.actions.act_window",
            "res_model": "sale.delivery.line.match",
            "views": [
                (
                    self.env.ref("sale_stock.sale_delivery_line_match_list").id,
                    "list",
                ),
            ],
            "domain": [
                ("company_id", "in", self.env.company.ids),
                (
                    "partner_id",
                    "in",
                    (self.partner_id | self.partner_id.commercial_partner_id).ids,
                ),
                "|",
                ("order_id", "=", self.id),
                "&",
                ("order_id", "=", False),
                ("product_id", "in", self.line_ids.product_id.ids),
            ],
        }
