from odoo import fields, models
from odoo.libs.sql import SQL

CURRENCY_RATE = "COALESCE(NULLIF(s.currency_rate, 0), 1.0)"


class ReportPosOrder(models.Model):
    _name = "report.pos.order"
    _inherit = "mixin.order.report"
    _description = "Point of Sale Orders Report"
    _auto = False
    _order = "date_order desc"
    _rec_name = "order_id"

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
    )
    product_uom_qty = fields.Float(
        string="Product Quantity",
        readonly=True,
    )
    price_average = fields.Monetary(
        string="Average Price",
        readonly=True,
        aggregator="avg",
    )
    price_subtotal_nodiscount = fields.Monetary(
        string="Subtotal w/o Discount",
        readonly=True,
    )
    discount_amount = fields.Monetary(readonly=True)
    margin = fields.Monetary(readonly=True)
    delay_validation = fields.Integer(readonly=True)
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
            payment_method_by_order_line AS (
                -- Map each "pos_order_line" to the "payment_method_id" of its
                -- "pos_order", always showing the first one.
                SELECT
                    pol.id AS pos_order_line_id,
                    pm.pos_order_id AS pos_order_id,
                    (array_agg(pm.payment_method_id ORDER BY pm.id ASC))[1] AS payment_method_id
                FROM pos_order_line pol
                LEFT JOIN pos_order po ON (po.id = pol.order_id)
                LEFT JOIN pos_payment pm ON (pm.pos_order_id = po.id)
                GROUP BY pol.id, pm.pos_order_id
            ),
            first_pos_category AS (
                SELECT
                    pt.id AS product_template_id,
                    -- ORDER BY makes the pick deterministic: a product template may
                    -- belong to several PoS categories, and without it the reported
                    -- pos_categ_id could differ between runs of the same query.
                    (array_agg(pc.id ORDER BY pc.id))[1] AS id
                FROM product_template pt
                LEFT JOIN pos_category_product_template_rel pcpt ON (pt.id = pcpt.product_template_id)
                LEFT JOIN pos_category pc ON (pcpt.pos_category_id = pc.id)
                GROUP BY pt.id
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
            "journal_id": "s.sale_journal",
            "config_id": "ps.config_id",
            "session_id": "s.session_id",
            "pricelist_id": "s.pricelist_id",
            "payment_method_id": "pm.payment_method_id",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
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
                    WHEN l.qty * u.factor = 0 THEN NULL
                    ELSE (l.qty * l.price_unit / {CURRENCY_RATE}) / (l.qty * u.factor)::decimal
                END""",
            "margin": f"(l.price_subtotal - COALESCE(l.total_cost, 0)) / {CURRENCY_RATE}",
            "delay_validation": """cast(
                    to_char(
                        date_trunc('day', s.date_order) - date_trunc('day', s.create_date),
                        'DD'
                    ) AS INT
                )""",
        }

    def _get_from_tables(self) -> list:
        return [
            ("pos_order_line", "l", None, None),
            ("pos_order", "s", "INNER JOIN", "s.id = l.order_id"),
            ("product_product", "p", "LEFT JOIN", "l.product_id = p.id"),
            ("product_template", "pt", "LEFT JOIN", "p.product_tmpl_id = pt.id"),
            ("uom_uom", "u", "LEFT JOIN", "u.id = pt.uom_id"),
            ("pos_session", "ps", "LEFT JOIN", "s.session_id = ps.id"),
            ("res_company", "co", "LEFT JOIN", "s.company_id = co.id"),
            ("res_currency", "cu", "LEFT JOIN", "co.currency_id = cu.id"),
            (
                "payment_method_by_order_line",
                "pm",
                "LEFT JOIN",
                "pm.pos_order_line_id = l.id",
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
