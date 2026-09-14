from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.sale import const

_debug = DebugLog(__name__)


class SaleReport(models.Model):
    _name = "sale.report"
    _inherit = "mixin.order.report"
    _description = "Sales Analysis Report"
    _auto = False
    _order = "date_order desc"

    order_reference = fields.Reference(
        selection=[("sale.order", "Sales Order")],
        string="Order",
        aggregator="count_distinct",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer Entity",
        readonly=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Customer Country",
        readonly=True,
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Customer State",
        readonly=True,
    )
    partner_zip = fields.Char(
        string="Customer ZIP",
        readonly=True,
    )
    industry_id = fields.Many2one(
        comodel_name="res.partner.industry",
        string="Customer Industry",
        readonly=True,
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        readonly=True,
    )
    campaign_id = fields.Many2one(
        comodel_name="utm.campaign",
        readonly=True,
    )
    medium_id = fields.Many2one(
        comodel_name="utm.medium",
        readonly=True,
    )
    source_id = fields.Many2one(
        comodel_name="utm.source",
        readonly=True,
    )
    name = fields.Char(
        string="Order Reference",
        readonly=True,
    )
    state = fields.Selection(
        selection=const.ORDER_STATE,
        string="Status",
        readonly=True,
    )
    sent = fields.Boolean(readonly=True)
    invoice_state = fields.Selection(
        selection=const.INVOICE_STATE,
        string="Order Invoice Status",
        readonly=True,
    )
    line_invoice_state = fields.Selection(
        selection=const.INVOICE_STATE,
        string="Invoice Status",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product Variant",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        readonly=True,
    )
    qty_transferred = fields.Float(
        string="Qty Delivered",
        readonly=True,
    )
    qty_to_transfer = fields.Float(
        string="Qty To Deliver",
        readonly=True,
    )
    qty_invoiced = fields.Float(readonly=True)
    qty_to_invoice = fields.Float(readonly=True)
    price_average = fields.Monetary(
        string="Average Price",
        readonly=True,
        aggregator="avg",
        help="Quantity-weighted average sale price (not a cost).",
    )
    discount = fields.Float(
        string="Discount %",
        readonly=True,
        aggregator="avg",
    )
    discount_amount = fields.Monetary(readonly=True)
    amount_taxexc_invoiced = fields.Monetary(
        string="Untaxed Amount Invoiced",
        readonly=True,
    )
    amount_taxexc_to_invoice = fields.Monetary(
        string="Untaxed Amount To Invoice",
        readonly=True,
    )

    @api.model
    def _get_done_states(self):
        return ["done"]

    def _case_value_or_one(self, value):
        return f"""CASE COALESCE({value}, 0) WHEN 0 THEN 1.0 ELSE {value} END"""

    def _get_fields_select(self) -> dict:
        currency_rate_o = self._case_value_or_one("o.currency_rate")
        currency_rate_table = self._case_value_or_one("account_currency_table.rate")

        fields = {
            "id": "MIN(l.id)",
            "order_reference": "CONCAT('sale.order', ',', o.id)",
            "company_id": "o.company_id",
            "currency_id": str(self.env.company.currency_id.id),
            "partner_id": "o.partner_id",
            "commercial_partner_id": "partner.commercial_partner_id",
            "country_id": "partner.country_id",
            "state_id": "partner.state_id",
            "partner_zip": "partner.zip",
            "industry_id": "partner.primary_industry_id",
            "pricelist_id": "o.pricelist_id",
            "user_id": "o.user_id",
            "campaign_id": "o.campaign_id",
            "medium_id": "o.medium_id",
            "source_id": "o.source_id",
            "date_order": "o.date_order",
            "name": "o.name",
            "state": "o.state",
            "sent": "o.sent",
            "invoice_state": "o.invoice_state",
            "line_invoice_state": "l.invoice_state",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
            "product_category_id": "t.categ_id",
            "product_uom_id": "t.uom_id",
            "product_uom_qty": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.product_qty * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_transferred": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.qty_transferred * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_to_transfer": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM((l.product_qty - l.qty_transferred) * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_invoiced": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.qty_invoiced * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_to_invoice": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.qty_to_invoice * u.factor / u2.factor)
                    ELSE 0
                END""",
            "price_unit": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN AVG(
                        l.price_unit
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "price_average": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN (
                        SUM(
                            l.product_qty * l.price_unit
                            / {currency_rate_o}
                            * {currency_rate_table}
                        ) / NULLIF(
                            SUM(
                                l.product_qty * u.factor / u2.factor
                            ),
                            0.0
                        )
                    )
                    ELSE 0
                END""",
            "price_subtotal": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(
                        l.price_subtotal
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "price_total": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(
                        l.price_total
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "discount": "l.discount",
            "discount_amount": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(
                        l.price_unit * l.product_qty * l.discount / 100.0
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "amount_taxexc_invoiced": f"""CASE WHEN l.product_id IS NOT NULL OR l.is_downpayment
                    THEN SUM(
                        l.amount_taxexc_invoiced
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "amount_taxexc_to_invoice": f"""CASE WHEN l.product_id IS NOT NULL OR l.is_downpayment
                    THEN SUM(
                        l.amount_taxexc_to_invoice
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "weight": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(p.weight * l.product_qty * u.factor / u2.factor)
                    ELSE 0
                END""",
            "volume": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(p.volume * l.product_qty * u.factor / u2.factor)
                    ELSE 0
                END""",
            "nbr_lines": "COUNT(*)",
        }

        additional_fields = self._select_additional_fields()
        fields.update(additional_fields)
        _debug.pipeline(
            "report_fields_select",
            columns=len(fields),
            additional=len(additional_fields),
        )

        return fields

    def _get_from_tables(self) -> list:
        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies,
        )
        _debug.perf.count("report_currency_table", companies=self.env.companies)

        return [
            ("sale_order_line", "l", None, None),
            ("sale_order", "o", "LEFT JOIN", "l.order_id=o.id"),
            ("res_partner", "partner", "LEFT JOIN", "o.partner_id=partner.id"),
            (
                currency_table,
                "account_currency_table",
                "LEFT JOIN",
                "o.company_id=account_currency_table.company_id",
            ),
            ("product_product", "p", "LEFT JOIN", "l.product_id=p.id"),
            ("product_template", "t", "LEFT JOIN", "p.product_tmpl_id=t.id"),
            ("uom_uom", "u", "LEFT JOIN", "l.product_uom_id=u.id"),
            ("uom_uom", "u2", "LEFT JOIN", "t.uom_id=u2.id"),
        ]

    def _get_fields_group_by(self) -> list:
        return [
            "l.product_id",
            "l.order_id",
            "l.price_unit",
            "l.invoice_state",
            "t.uom_id",
            "t.categ_id",
            "o.name",
            "o.date_order",
            "o.partner_id",
            "o.user_id",
            "o.state",
            "o.sent",
            "o.invoice_state",
            "o.company_id",
            "o.campaign_id",
            "o.medium_id",
            "o.source_id",
            "o.pricelist_id",
            "p.product_tmpl_id",
            "partner.commercial_partner_id",
            "partner.country_id",
            "partner.primary_industry_id",
            "partner.state_id",
            "partner.zip",
            "l.is_downpayment",
            "l.discount",
            "o.id",
            "account_currency_table.rate",
        ]

    def _select_additional_fields(self):
        return {}
