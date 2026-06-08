# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.models import TableSQL
from odoo.tools import SQL

from odoo.addons.sale.models.sale_order import SALE_ORDER_STATE


class SaleReport(models.Model):
    _name = "sale.report"
    _description = "Sales Analysis Report"
    _auto = False
    _rec_name = "date"
    _order = "date desc"

    @api.model
    def _get_done_states(self):
        return ["sale"]

    @api.model
    def _selection_target_model(self):
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
            if not model.is_transient()
        ]

    # sale.order fields
    name = fields.Char(string="Order Reference", readonly=True)
    line_name = fields.Char(string="Order Line Name", readonly=True)
    date = fields.Datetime(string="Order Date", readonly=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer", readonly=True)
    company_id = fields.Many2one(comodel_name="res.company", readonly=True)
    pricelist_id = fields.Many2one(comodel_name="product.pricelist", readonly=True)
    team_id = fields.Many2one(comodel_name="crm.team", string="Sales Team", readonly=True)
    user_id = fields.Many2one(comodel_name="res.users", string="Salesperson", readonly=True)
    state = fields.Selection(selection=SALE_ORDER_STATE, string="Status", readonly=True)
    invoice_status = fields.Selection(
        selection=[
            ("upselling", "Upselling Opportunity"),
            ("invoiced", "Fully Invoiced"),
            ("to invoice", "To Invoice"),
            ("no", "Nothing to Invoice"),
        ],
        string="Order Invoice Status",
        readonly=True,
    )

    campaign_id = fields.Many2one(comodel_name="utm.campaign", string="Campaign", readonly=True)
    medium_id = fields.Many2one(comodel_name="utm.medium", string="Medium", readonly=True)
    source_id = fields.Many2one(comodel_name="utm.source", string="Source", readonly=True)
    utm_reference = fields.Reference(string="UTM Reference", selection="_selection_target_model")

    # res.partner fields
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner", string="Customer Entity", readonly=True
    )
    country_id = fields.Many2one(
        comodel_name="res.country", string="Customer Country", readonly=True
    )
    industry_id = fields.Many2one(
        comodel_name="res.partner.industry", string="Customer Industry", readonly=True
    )
    partner_zip = fields.Char(string="Customer ZIP", readonly=True)
    state_id = fields.Many2one(
        comodel_name="res.country.state", string="Customer State", readonly=True
    )
    partner_tag_ids = fields.Many2many(
        string="Customer Tags", related="partner_id.category_id", readonly=True
    )

    # sale.order.line fields
    order_reference = fields.Reference(
        string="Order", selection=[("sale.order", "Sales Order")], aggregator="count_distinct"
    )

    categ_id = fields.Many2one(
        comodel_name="product.category", string="Product Category", readonly=True
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product Variant", readonly=True
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Product", readonly=True
    )
    product_uom_id = fields.Many2one(comodel_name="uom.uom", string="Unit", readonly=True)
    product_uom_qty = fields.Float(string="Qty Ordered", readonly=True)
    qty_to_deliver = fields.Float(string="Qty To Deliver", readonly=True)
    qty_delivered = fields.Float(string="Qty Delivered", readonly=True)
    qty_to_invoice = fields.Float(string="Qty To Invoice", readonly=True)
    qty_invoiced = fields.Float(string="Qty Invoiced", readonly=True)
    price_subtotal = fields.Monetary(string="Untaxed Total", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)
    untaxed_amount_to_invoice = fields.Monetary(string="Untaxed Amount To Invoice", readonly=True)
    untaxed_amount_invoiced = fields.Monetary(string="Untaxed Amount Invoiced", readonly=True)
    untaxed_delivered_amount = fields.Monetary(string="Untaxed Amount Delivered", readonly=True)
    line_invoice_status = fields.Selection(
        selection=[
            ("upselling", "Upselling Opportunity"),
            ("invoiced", "Fully Invoiced"),
            ("to invoice", "To Invoice"),
            ("no", "Nothing to Invoice"),
        ],
        string="Invoice Status",
        readonly=True,
    )

    weight = fields.Float(string="Gross Weight", readonly=True)
    volume = fields.Float(string="Volume", readonly=True)
    price_unit = fields.Float(string="Unit Price", aggregator="avg", readonly=True)
    discount = fields.Float(string="Discount %", readonly=True, aggregator="avg")
    discount_amount = fields.Monetary(string="Discount Amount", readonly=True)

    # aggregates or computed fields
    nbr = fields.Integer(string="# of Lines", readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", readonly=True)

    @property
    def _table_query(self) -> SQL:
        today = fields.Date.today()
        query = self.env['sale.order.line'].sudo().with_context(date_to=today)._search(self._order_line_domain())
        query.groupby = SQL(", ").join(self._groupby_list(query.table))
        return query.subselect(*self._select_dict_to_list(self._select_dict(query.table)))

    def _order_line_domain(self):
        return Domain('display_type', '=', False)

    def _select_dict_to_list(self, select_dict):
        return [SQL("%s AS %s", select_dict.get(fname, SQL("NULL")), SQL.identifier(fname)) for fname, field in self._fields.items() if field.store]

    def _select_dict(self, table: TableSQL):
        uom_ratio = SQL("(COALESCE(%s, 1) / NULLIF(COALESCE(%s, 1), 0.0))", table.product_uom_id.factor, table.product_id.uom_id.factor)
        order_rate = self._case_value_or_one(table.order_id.currency_rate)
        rate = SQL("%s / %s", table.consolidation_rate, order_rate)
        return {
            'id': SQL("MIN(%s)", table.id),
            'product_id': table.product_id,
            'line_name': table.name,
            'line_invoice_status': SQL("%s", table.invoice_status),
            'product_uom_id': SQL("CASE WHEN %s IS NULL THEN %s ELSE %s END", table.product_id, table.product_id.uom_id, table.product_uom_id),
            'product_uom_qty': SQL("CASE WHEN %s IS NOT TRUE THEN SUM(%s * %s) ELSE 0 END", table.is_downpayment, table.product_uom_qty, uom_ratio),
            'qty_delivered': SQL("CASE WHEN %s IS NOT TRUE THEN SUM(%s * %s) ELSE 0 END", table.is_downpayment, table.qty_delivered, uom_ratio),
            'qty_to_deliver': SQL("CASE WHEN %s IS NOT TRUE THEN SUM((%s - %s) * %s) ELSE 0 END", table.is_downpayment, table.product_uom_qty, table.qty_delivered, uom_ratio),
            'qty_invoiced': SQL("CASE WHEN %s IS NOT TRUE THEN SUM(%s * %s) ELSE 0 END", table.is_downpayment, table.qty_invoiced, uom_ratio),
            'qty_to_invoice': SQL("CASE WHEN %s IS NOT TRUE THEN SUM(%s * %s) ELSE 0 END", table.is_downpayment, table.qty_to_invoice, uom_ratio),
            'price_unit': SQL("CASE WHEN %s IS NOT TRUE THEN AVG(%s * %s) ELSE 0 END", table.is_downpayment, table.price_unit, rate),
            'price_total': SQL("CASE WHEN %s IS NOT TRUE THEN SUM(%s * %s) ELSE 0 END", table.is_downpayment, table.price_total, rate),
            'price_subtotal': SQL("CASE WHEN %s IS NOT TRUE THEN SUM(%s * %s) ELSE 0 END", table.is_downpayment, table.price_subtotal, rate),
            'untaxed_amount_to_invoice': SQL("SUM(%s * %s)", table.untaxed_amount_to_invoice, rate),
            'untaxed_amount_invoiced': SQL("SUM(%s * %s)", table.untaxed_amount_invoiced, rate),
            'untaxed_delivered_amount': SQL("SUM(%s * %s * %s)", table.price_unit, table.qty_delivered, rate),
            'nbr': SQL("COUNT(*)"),
            'name': table.order_id.name,
            'date': SQL("%s", table.order_id.date_order),
            'state': table.order_id.state,
            'invoice_status': table.order_id.invoice_status,
            'partner_id': table.order_id.partner_id,
            'user_id': table.order_id.user_id,
            'company_id': table.order_id.company_id,
            'campaign_id': table.order_id.campaign_id,
            'medium_id': table.order_id.medium_id,
            'source_id': table.order_id.source_id,
            'utm_reference': table.order_id.utm_reference,
            'categ_id': table.product_id.categ_id,
            'pricelist_id': table.order_id.pricelist_id,
            'team_id': table.order_id.team_id,
            'product_tmpl_id': table.product_id.product_tmpl_id,
            'commercial_partner_id': table.order_id.partner_id.commercial_partner_id,
            'country_id': table.order_id.partner_id.country_id,
            'industry_id': table.order_id.partner_id.industry_id,
            'state_id': table.order_id.partner_id.state_id,
            'partner_zip': SQL("%s", table.order_id.partner_id.zip),
            'weight': SQL("SUM(%s * %s * %s)", table.product_id.weight, table.product_uom_qty, uom_ratio),
            'volume': SQL("SUM(%s * %s * %s)", table.product_id.volume, table.product_uom_qty, uom_ratio),
            'discount': table.discount,
            'discount_amount': SQL("SUM(%s * %s * %s * %s)", table.price_unit, table.product_uom_qty, table.discount, rate),
            'currency_id': SQL("%s", self.env.company.currency_id.id),
            'order_reference': SQL("concat('sale.order', ',', %s)", table.order_id),
        }

    def _groupby_list(self, table: TableSQL):
        return [
            table.product_id,
            table.price_unit,
            table.invoice_status,
            table.name,
            table.product_uom_id,
            table.is_downpayment,
            table.discount,
            table.order_id,
            table.order_id.id,
            table.product_id.uom_id,
            table.product_id.product_tmpl_id,
            table.product_id.product_tmpl_id.id,
            table.order_id.partner_id.id,
        ]

    def _case_value_or_one(self, value):
        return SQL("CASE COALESCE(%(value)s, 0) WHEN 0 THEN 1.0 ELSE %(value)s END", value=value)

    @api.readonly
    def action_open_order(self):
        self.ensure_one()
        return {
            "res_model": self.order_reference._name,
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "res_id": self.order_reference.id,
        }
