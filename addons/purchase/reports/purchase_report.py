from odoo import fields, models

from odoo.addons.purchase import const


class PurchaseReport(models.Model):
    _name = "purchase.report"
    _inherit = "mixin.order.report"
    _description = "Purchase Report"
    _auto = False
    _order = "date_order desc, price_total desc"

    order_reference = fields.Reference(
        selection=[("purchase.order", "Purchase Order")],
        string="Order",
        aggregator="count_distinct",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        readonly=True,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Commercial Entity",
        readonly=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Partner Country",
        readonly=True,
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Buyer",
        readonly=True,
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        readonly=True,
    )
    state = fields.Selection(
        selection=const.ORDER_STATE,
        string="Status",
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
        string="Reference Unit of Measure",
        readonly=True,
    )
    qty_transferred = fields.Float(
        string="Qty Received",
        readonly=True,
    )
    qty_invoiced = fields.Float(
        string="Qty Billed",
        readonly=True,
    )
    qty_to_invoice = fields.Float(
        string="Qty to be Billed",
        readonly=True,
    )
    price_average = fields.Monetary(
        string="Average Cost",
        readonly=True,
        aggregator="avg",
    )
    delay = fields.Float(
        string="Days to Confirm",
        digits=(16, 2),
        readonly=True,
        aggregator="avg",
        help="Amount of time between purchase confirmation and order by date.",
    )
    delay_pass = fields.Float(
        string="Days to Receive",
        digits=(16, 2),
        readonly=True,
        aggregator="avg",
        help="Amount of time between date planned and order by date for each purchase order line.",
    )

    def _get_fields_select(self) -> dict:
        return {
            "id": "MIN(l.id)",
            "order_reference": "CONCAT('purchase.order', ',', o.id)",
            "company_id": "o.company_id",
            "currency_id": "c.currency_id",
            "dest_address_id": "o.dest_address_id",
            "partner_id": "o.partner_id",
            "commercial_partner_id": "partner.commercial_partner_id",
            "country_id": "partner.country_id",
            "user_id": "o.user_id",
            "fiscal_position_id": "o.fiscal_position_id",
            "date_order": "o.date_order",
            "date_confirmed": "o.date_confirmed",
            "state": "o.state",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
            "product_category_id": "t.categ_id",
            "product_uom_id": "t.uom_id",
            "delay": """EXTRACT(
                    EPOCH FROM age(
                        o.date_confirmed, o.date_order
                    )
                ) / (24 * 60 * 60)::decimal(16,2)""",
            "delay_pass": """EXTRACT(
                    EPOCH FROM age(
                        l.date_commitment, o.date_order
                    )
                ) / (24 * 60 * 60)::decimal(16,2)""",
            "product_uom_qty": """SUM(
                    l.product_qty * line_uom.factor / product_uom_id.factor
                )""",
            "qty_transferred": """SUM(
                    l.qty_transferred * line_uom.factor / product_uom_id.factor
                )""",
            "qty_invoiced": """SUM(
                    l.qty_invoiced * line_uom.factor / product_uom_id.factor
                )""",
            "qty_to_invoice": """CASE WHEN t.bill_policy = 'ordered'
                    THEN SUM(l.product_qty * line_uom.factor / product_uom_id.factor) - SUM(l.qty_invoiced * line_uom.factor / product_uom_id.factor)
                    ELSE SUM(l.qty_transferred * line_uom.factor / product_uom_id.factor) - SUM(l.qty_invoiced * line_uom.factor / product_uom_id.factor)
                END""",
            "price_unit": """AVG(
                    l.price_unit / COALESCE(o.currency_rate, 1.0)
                )::decimal(16,2) * account_currency_table.rate""",
            "price_average": """(
                    SUM(
                        l.product_qty * l.price_unit / COALESCE(o.currency_rate, 1.0)
                    ) / NULLIF(
                        SUM(
                            l.product_qty * line_uom.factor / product_uom_id.factor
                        ),
                        0.0
                    )
                )::decimal(16,2) * account_currency_table.rate""",
            "price_total": """SUM(
                    l.price_total / COALESCE(o.currency_rate, 1.0)
                )::decimal(16,2) * account_currency_table.rate""",
            "weight": """SUM(
                    p.weight * l.product_qty * line_uom.factor / product_uom_id.factor
                )""",
            "volume": """SUM(
                    p.volume * l.product_qty * line_uom.factor / product_uom_id.factor
                )""",
            "price_subtotal": """SUM(
                    l.price_subtotal / COALESCE(o.currency_rate, 1.0)
                )::decimal(16,2) * account_currency_table.rate""",
            "nbr_lines": "COUNT(*)",
        }

    def _get_from_tables(self) -> list:
        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies,
        )

        return [
            ("purchase_order_line", "l", None, None),
            ("purchase_order", "o", "LEFT JOIN", "l.order_id=o.id"),
            ("res_partner", "partner", "LEFT JOIN", "o.partner_id=partner.id"),
            (
                currency_table,
                "account_currency_table",
                "LEFT JOIN",
                "o.company_id=account_currency_table.company_id",
            ),
            ("product_product", "p", "LEFT JOIN", "l.product_id=p.id"),
            ("product_template", "t", "LEFT JOIN", "p.product_tmpl_id=t.id"),
            ("res_company", "c", "LEFT JOIN", "o.company_id=c.id"),
            ("uom_uom", "line_uom", "LEFT JOIN", "l.product_uom_id=line_uom.id"),
            ("uom_uom", "product_uom_id", "LEFT JOIN", "t.uom_id=product_uom_id.id"),
        ]

    def _get_fields_group_by(self) -> list:
        return [
            "o.company_id",
            "o.user_id",
            "o.partner_id",
            "line_uom.factor",
            "c.currency_id",
            "l.price_unit",
            "o.date_confirmed",
            "l.date_commitment",
            "l.product_uom_id",
            "o.dest_address_id",
            "o.fiscal_position_id",
            "l.product_id",
            "p.product_tmpl_id",
            "t.categ_id",
            "o.date_order",
            "o.state",
            "t.uom_id",
            "t.bill_policy",
            "line_uom.id",
            "product_uom_id.factor",
            "partner.country_id",
            "partner.commercial_partner_id",
            "o.id",
            "account_currency_table.rate",
        ]
