import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.sale.order",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )
    has_done_picking = fields.Boolean(
        string="Has Done Picking", compute="_compute_has_done_picking", store=True
    )
    woo_order_status = fields.Selection(
        selection=[
            ("completed", "Completed"),
            ("pending", "Pending payment"),
            ("processing", "Processing"),
            ("on-hold", "On hold"),
            ("cancelled", "Cancelled"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
            ("trash", "Trash"),
        ],
        string="WooCommerce Status",
    )
    woo_order_status_id = fields.Many2one(
        comodel_name="woo.sale.status",
        string="WooCommerce Order Status",
        ondelete="restrict",
    )
    is_final_status = fields.Boolean(
        related="woo_order_status_id.is_final_status", string="Final Status"
    )
    woo_order_status_code = fields.Char(related="woo_order_status_id.code")
    tax_different = fields.Boolean(compute="_compute_tax_different")
    total_amount_different = fields.Boolean(compute="_compute_total_amount_different")
    woo_coupon = fields.Char()
    woo_payment_mode_id = fields.Many2one(
        comodel_name="woo.payment.gateway",
        string="WooCommerce Payment Mode",
        readonly=True,
    )
    is_fully_returned = fields.Boolean(
        string="Fully Returned",
        compute="_compute_is_fully_returned",
        store=True,
        readonly=True,
    )

    @api.depends(
        "order_line.qty_delivered",
        "order_line.product_uom_qty",
        "picking_ids",
        "picking_ids.is_return_stock_picking",
    )
    def _compute_is_fully_returned(self):
        """
        Compute the 'is_fully_returned' field for the sale order.

        This method checks whether all products in the sale order have been fully
        returned. It considers pickings with a refund and checks if the total quantity
        done in those pickings is equal to the ordered quantity.
        """
        for order in self:
            flag_fully_return = True
            return_pickings = order.picking_ids.filtered(
                lambda p: p.is_return_stock_picking
            )
            if not return_pickings:
                order.is_fully_returned = False
                continue
            for order_line in order.order_line:
                total_quantity_done = sum(
                    move.quantity_done
                    for move in order.picking_ids.mapped("move_ids")
                    if (
                        move.origin_returned_move_id
                        and move.product_id == order_line.product_id
                    )
                )
                if total_quantity_done != order_line.product_uom_qty:
                    flag_fully_return = False
                    break
            order.is_fully_returned = flag_fully_return

    @api.depends(
        "woo_bind_ids",
        "order_line.woo_bind_ids.total_tax_line",
        "order_line.price_tax",
    )
    def _compute_tax_different(self):
        """
        Compute the 'tax_different' field for the sale order.

        This method calculates whether the tax amounts on WooCommerce order lines
        are different from the total tax amount of the order binding. If there is any
        inconsistency, it sets the 'tax_different' field to True; otherwise, it remains
        False.
        """
        for order in self:
            tax_different = False
            rounding = order.currency_id.rounding
            if any(
                [
                    float_compare(
                        line.price_tax,
                        line.total_tax_line,
                        precision_rounding=rounding,
                    )
                    != 0
                    for line in order.mapped("woo_bind_ids").mapped(
                        "woo_order_line_ids"
                    )
                ]
            ):
                tax_different = True
            order.tax_different = tax_different

    @api.depends("amount_total", "woo_bind_ids.woo_amount_total")
    def _compute_total_amount_different(self):
        """
        Compute the 'total_amount_different' field for each record in the current
        recordset.

        This method is used to calculate whether there is a difference in the total
        amount between the current sales order and its related WooCommerce bindings.
        The 'total_amount_different' field indicates whether the total amounts differ
        among the bindings.
        """
        for order in self:
            amount_total_different = False
            rounding = order.currency_id.rounding
            if any(
                [
                    float_compare(
                        order.amount_total,
                        binding.woo_amount_total,
                        precision_rounding=rounding,
                    )
                    != 0
                    for binding in order.mapped("woo_bind_ids")
                ]
            ):
                amount_total_different = True
            order.total_amount_different = amount_total_different

    @api.depends("picking_ids", "picking_ids.state")
    def _compute_has_done_picking(self):
        """Check all Picking is in done state"""
        for order in self:
            if not order.picking_ids:
                order.has_done_picking = False
            else:
                order.has_done_picking = all(
                    picking.state in ["done", "cancel"] for picking in order.picking_ids
                )

    def export_delivery_status(self):
        """Change state of a sales order on WooCommerce"""
        for binding in self.woo_bind_ids:
            if not binding.backend_id.mark_completed:
                raise ValidationError(
                    _(
                        "Export Delivery Status is Not Allow from WooCommerce"
                        " Backend '%s'.",
                        binding.backend_id.name,
                    )
                )
            binding.update_woo_order_fulfillment_status()


class WooSaleOrder(models.Model):
    _name = "woo.sale.order"
    _inherit = "woo.binding"
    _inherits = {"sale.order": "odoo_id"}
    _description = "WooCommerce Sale Order"

    _rec_name = "name"

    odoo_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        required=True,
        ondelete="restrict",
    )
    woo_order_line_ids = fields.One2many(
        comodel_name="woo.sale.order.line",
        inverse_name="woo_order_id",
        string="WooCommerce Order Lines",
        copy=False,
    )
    woo_order_id = fields.Integer(
        string="WooCommerce Order ID", help="'order_id' field in WooCommerce"
    )
    discount_total = fields.Monetary()
    discount_tax = fields.Monetary()
    shipping_total = fields.Monetary()
    shipping_tax = fields.Monetary()
    cart_tax = fields.Monetary()
    total_tax = fields.Monetary()
    price_unit = fields.Monetary()
    woo_amount_total = fields.Monetary()

    def validate_delivery_orders_done(self):
        """
        Add validations on creation and process of fulfillment orders
        based on delivery order state.
        """
        picking_ids = self.mapped("picking_ids").filtered(
            lambda p: p.state == "done" and p.picking_type_id.code == "outgoing"
        )
        if not picking_ids:
            raise ValidationError(_("No delivery orders in 'done' state."))
        if self.is_final_status:
            raise ValidationError(
                _("WooCommerce Sale Order is already in Completed Status.")
            )
        for woo_order in self:
            no_tracking_do = picking_ids.filtered(lambda p: not p.carrier_tracking_ref)
            if woo_order.backend_id.tracking_info and no_tracking_do:
                do_names = ", ".join(no_tracking_do.mapped("name"))
                raise ValidationError(
                    _("Tracking Reference not found in Delivery Order! %s" % do_names)
                )

    def update_woo_order_fulfillment_status(self, job_options=None):
        """Change status of a sales order on WooCommerce"""
        woo_model = self.env["woo.sale.order"]
        if self._context.get("execute_from_cron"):
            if job_options is None:
                job_options = {}
            if "description" not in job_options:
                description = self.export_record.__doc__
                job_options["description"] = self.backend_id.get_queue_job_description(
                    description, self._description
                )
            woo_model = woo_model.with_company(self.backend_id.company_id).with_delay(
                **job_options or {}
            )
        for woo_order in self:
            if not self._context.get("execute_from_cron"):
                woo_order.validate_delivery_orders_done()
            woo_model.export_record(woo_order.backend_id, woo_order)


class WooSaleOrderAdapter(Component):
    _name = "woo.sale.order.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.sale.order"

    _woo_model = "orders"
    _woo_key = "id"
    _woo_ext_id_key = "id"
    _model_dependencies = [
        (
            "woo.res.partner",
            "customer_id",
        ),
    ]


# Sale order line


class WooSaleOrderLine(models.Model):
    _name = "woo.sale.order.line"
    _inherit = "woo.binding"
    _description = "WooCommerce Sale Order Line"
    _inherits = {"sale.order.line": "odoo_id"}

    woo_order_id = fields.Many2one(
        comodel_name="woo.sale.order",
        string="WooCommerce Order Line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    odoo_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order Line",
        required=True,
        ondelete="restrict",
    )
    total_tax_line = fields.Monetary()
    price_subtotal_line = fields.Monetary(string="Total Line")
    subtotal_tax_line = fields.Monetary()
    subtotal_line = fields.Monetary()

    @api.model_create_multi
    def create(self, vals):
        """
        Create multiple WooSaleOrderLine records.

        :param vals: List of dictionaries containing values for record creation.
        :type vals: list of dict
        :return: Created WooSaleOrderLine records.
        :rtype: woo.sale.order.line
        """
        for value in vals:
            existing_record = self.search(
                [
                    ("external_id", "=", value.get("external_id")),
                    ("backend_id", "=", value.get("backend_id")),
                ]
            )
            if not existing_record:
                binding = self.env["woo.sale.order"].browse(value["woo_order_id"])
                value["order_id"] = binding.odoo_id.id
        return super(WooSaleOrderLine, self).create(vals)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.sale.order.line",
        inverse_name="odoo_id",
        string="WooCommerce Bindings(Order Line)",
        copy=False,
    )
    woo_line_id = fields.Char()
