from odoo import api, fields, models


class BaseOrderTestLine(models.Model):
    _name = "base.order.test.line"
    _inherit = [
        "mixin.order.line.fields",
        "mixin.order.line.amount",
        "mixin.order.line.invoice",
        "mixin.analytic",
    ]
    _description = "Base Order Test Line"

    # FIELDS

    # Only ``comodel_name`` differs from ``mixin.order.line.fields``, which
    # also supplies the bridge fields (company_id, currency_id, state,
    # partner_id, locked, …) — as in the real sale/purchase lines.
    order_id = fields.Many2one(
        comodel_name="base.order.test",
        string="Order",
    )

    # Self-referential section link: the compute lives in the mixin, but the
    # comodel must point to this concrete line model (as in sale/purchase).
    parent_id = fields.Many2one(comodel_name="base.order.test.line")

    # The order-line side of the link to `account.move.line`. Declared on the
    # mixin without a relation table, so a concrete model that does not name
    # one shares nothing with its invoice lines and every search over
    # `invoice_ids` comes back empty.
    invoice_line_ids = fields.Many2many(
        relation="account_move_line_base_order_test_line_rel",
        column1="order_line_id",
        column2="move_line_id",
    )

    # ROUTING

    _order_type = "sale"
    _product_ok_field = "sale_ok"
    _analytic_business_domain = "sale_order"
    _product_tax_field = "taxes_id"
    _invoice_move_direction = "out"
    _invoice_policy_field = "base_order_test_invoice_policy"
    _price_direction = 1

    # INVOICING METHODS

    #: Test input. `_compute_invoice_amounts` is abstract on the mixin because
    #: only a concrete model knows where invoiced quantities come from; here
    #: they come from this field, so a test can put a line into any invoicing
    #: state -- including over-invoiced -- without an `account.move`.
    qty_invoiced_input = fields.Float(digits="Product Unit")

    @api.depends("product_qty", "price_unit", "qty_invoiced_input")
    def _compute_invoice_amounts(self):
        for line in self:
            if line.display_type:
                line.qty_invoiced = 0.0
                line.qty_to_invoice = 0.0
                line.amount_taxexc_invoiced = 0.0
                line.amount_taxinc_invoiced = 0.0
                line.amount_taxexc_to_invoice = 0.0
                line.amount_taxinc_to_invoice = 0.0
                continue
            price = line.price_unit or 0.0
            line.qty_invoiced = line.qty_invoiced_input
            line.qty_to_invoice = (line.product_qty or 0.0) - line.qty_invoiced
            line.amount_taxexc_invoiced = line.qty_invoiced * price
            line.amount_taxinc_invoiced = line.amount_taxexc_invoiced
            line.amount_taxexc_to_invoice = line.qty_to_invoice * price
            line.amount_taxinc_to_invoice = line.amount_taxexc_to_invoice

    # No `_compute_invoice_state` override on purpose: the mixin's own state
    # machine is what this module exists to exercise, and an override here
    # would leave it running in production and asserted by nothing.
    @api.depends(
        "qty_to_invoice",
        "qty_invoiced",
        "product_qty",
        "qty_transferred",
        "is_downpayment",
        "amount_taxexc_to_invoice",
        "product_id.base_order_test_invoice_policy",
    )
    def _compute_invoice_state(self):
        return super()._compute_invoice_state()

    # ─── Hooks consumed by later tasks (trivial stubs) ─────────────

    def _get_invoice_line_link_field(self):
        return "base_order_test_line_ids"

    def _get_default_line_description(self):
        return self.product_id.display_name or "/"

    def _get_auto_price_and_discount(self):
        self.check_singleton()
        return (self.product_id.list_price, 0.0)

    def _is_price_update_blocked(self):
        return False

    def _get_fields_tracked_qty(self):
        return ["product_qty"]

    def _post_quantity_changes(self, field_name, changes):
        for change in changes:
            change["line"].order_id.message_post(
                body=f"{field_name}: {change['old_qty']} -> {change['new_qty']}"
            )

    def _get_catalog_single_line_data(self, **kwargs):
        return {
            "quantity": self.product_qty,
            "price": self.price_unit,
            "readOnly": self.order_id._is_readonly(),
        }

    def _get_catalog_multi_line_data(self, **kwargs):
        return {"price": self.price_unit}
