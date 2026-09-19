from odoo import fields, models
from odoo.libs.sql import SQL

CURRENCY_RATE = "COALESCE(NULLIF(s.currency_rate, 0), 1.0)"


class ReportPosOrder(models.Model):
    _name = "report.pos.order"
    _inherit = "mixin.order.report"
    _description = "Point of Sale Orders Report"
    _auto = False
    _order = "date_order desc, id desc"
    _rec_name = "order_id"

    # The query reads source tables directly. Without these dependencies a
    # pending currency/configuration recomputation can leave analytics stale
    # even though the corresponding order already shows the new value.
    _depends = {
        "pos.order": [
            "date_order",
            "create_date",
            "partner_id",
            "state",
            "user_id",
            "company_id",
            "config_id",
            "session_id",
            "pricelist_id",
            "account_move",
            "currency_rate",
        ],
        "pos.order.line": [
            "order_id",
            "product_id",
            "qty",
            "price_unit",
            "price_subtotal",
            "price_subtotal_incl",
            "discount",
            "total_cost",
        ],
        "pos.config": ["journal_id"],
        "pos.payment": ["pos_order_id", "payment_method_id"],
        "product.product": ["product_tmpl_id", "weight", "volume"],
        "product.template": ["categ_id", "uom_id", "pos_categ_ids"],
        "res.company": ["currency_id"],
        "res.currency": ["decimal_places"],
    }

    order_id = fields.Many2one(
        comodel_name="pos.order",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        readonly=True,
    )
    pos_categ_id = fields.Many2one(
        comodel_name="pos.category",
        string="Point of Sale Category",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "New"),
            ("paid", "Paid"),
            ("done", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        readonly=True,
    )
    config_id = fields.Many2one(
        comodel_name="pos.config",
        string="Point of Sale",
        readonly=True,
    )
    session_id = fields.Many2one(
        comodel_name="pos.session",
        readonly=True,
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        readonly=True,
    )
    payment_method_id = fields.Many2one(
        comodel_name="pos.payment.method",
        readonly=True,
        help="First recorded payment method of the order; split payments do not split report lines.",
    )
    product_uom_qty = fields.Float(
        string="Product Quantity",
        readonly=True,
    )
    price_average = fields.Monetary(
        string="Average Price",
        readonly=True,
        aggregator="avg",
        help="Quantity-weighted price before discount, per product unit of measure, in company currency.",
    )
    price_subtotal_nodiscount = fields.Monetary(
        string="Subtotal w/o Discount",
        readonly=True,
    )
    discount_amount = fields.Monetary(readonly=True)
    margin = fields.Monetary(readonly=True)
    delay_validation = fields.Float(
        string="Days to Order",
        digits=(16, 2),
        readonly=True,
        aggregator="avg",
        help="Calendar days between order creation and the order date, averaged over order lines.",
    )
    invoiced = fields.Boolean(readonly=True)

    def action_view_order(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "views": [[False, "form"]],
            "res_id": self.order_id.id,
        }

    def _with_cte(self) -> SQL:
        return SQL("""
            first_payment_by_order AS (
                -- Pick once per order, before joining its lines. The lowest
                -- payment ID preserves the first-recorded-payment convention.
                SELECT DISTINCT ON (pos_order_id)
                    pos_order_id, payment_method_id
                FROM pos_payment
                ORDER BY pos_order_id, id
            ),
            first_pos_category AS (
                SELECT
                    product_template_id,
                    MIN(pos_category_id) AS id
                FROM pos_category_product_template_rel
                GROUP BY product_template_id
            )
        """)

    def _get_fields_select(self) -> dict:
        return {
            "id": "l.id",
            "nbr_lines": "1",
            "order_id": "s.id",
            "date_order": "s.date_order",
            "partner_id": "s.partner_id",
            "state": "s.state",
            "user_id": "s.user_id",
            "company_id": "s.company_id",
            "currency_id": "co.currency_id",
            "journal_id": "pc.journal_id",
            "config_id": "s.config_id",
            "session_id": "s.session_id",
            "pricelist_id": "s.pricelist_id",
            "payment_method_id": "pm.payment_method_id",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
            "product_uom_id": "pt.uom_id",
            "product_category_id": "pt.categ_id",
            "pos_categ_id": "fpc.id",
            "invoiced": "s.account_move IS NOT NULL",
            "product_uom_qty": "l.qty",
            "weight": "p.weight * l.qty",
            "volume": "p.volume * l.qty",
            "price_unit": f"l.price_unit / {CURRENCY_RATE}",
            "price_subtotal": f"ROUND(l.price_subtotal / {CURRENCY_RATE}, cu.decimal_places)",
            "price_total": f"ROUND(l.price_subtotal_incl / {CURRENCY_RATE}, cu.decimal_places)",
            "price_subtotal_nodiscount": f"l.qty * l.price_unit / {CURRENCY_RATE}",
            "discount_amount": f"(l.qty * l.price_unit) * (l.discount / 100) / {CURRENCY_RATE}",
            "price_average": f"""CASE
                    WHEN l.qty = 0 THEN NULL
                    ELSE l.price_unit / {CURRENCY_RATE}
                END""",
            "margin": f"(l.price_subtotal - COALESCE(l.total_cost, 0)) / {CURRENCY_RATE}",
            "delay_validation": "s.date_order::date - s.create_date::date",
        }

    def _get_from_tables(self) -> list:
        return [
            ("pos_order_line", "l", None, None),
            ("pos_order", "s", "INNER JOIN", "s.id = l.order_id"),
            ("product_product", "p", "LEFT JOIN", "l.product_id = p.id"),
            ("product_template", "pt", "LEFT JOIN", "p.product_tmpl_id = pt.id"),
            ("res_company", "co", "LEFT JOIN", "s.company_id = co.id"),
            ("pos_config", "pc", "LEFT JOIN", "s.config_id = pc.id"),
            ("res_currency", "cu", "LEFT JOIN", "co.currency_id = cu.id"),
            (
                "first_payment_by_order",
                "pm",
                "LEFT JOIN",
                "pm.pos_order_id = s.id",
            ),
            (
                "first_pos_category",
                "fpc",
                "LEFT JOIN",
                "pt.id = fpc.product_template_id",
            ),
        ]

    def _get_where_conditions(self) -> list:
        return []
