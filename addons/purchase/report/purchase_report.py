# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from odoo import fields, models
from odoo.models import TableSQL
from odoo.tools.sql import SQL


class PurchaseReport(models.Model):
    _name = 'purchase.report'
    _description = "Purchase Report"
    _auto = False
    _order = 'date_order desc, price_total desc'

    date_order = fields.Datetime('Order Deadline', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('cancel', 'Cancelled')
    ], 'Status', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    date_approve = fields.Datetime('Confirmation Date', readonly=True)
    uom_id = fields.Many2one('uom.uom', 'Reference Unit of Measure', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    user_id = fields.Many2one('res.users', 'Buyer', readonly=True)
    delay = fields.Float('Days to Confirm', digits=(16, 2), readonly=True, aggregator='avg', help="Amount of time between purchase approval and order by date.")
    delay_pass = fields.Float('Days to Receive', digits=(16, 2), readonly=True, aggregator='avg',
                              help="Amount of time between date planned and order by date for each purchase order line.")
    price_total = fields.Monetary('Total', readonly=True)
    price_average = fields.Monetary('Average Cost', readonly=True, aggregator="avg")
    nbr_lines = fields.Integer('# of Lines', readonly=True)
    category_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    country_id = fields.Many2one('res.country', 'Partner Country', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Commercial Entity', readonly=True)
    weight = fields.Float('Gross Weight', readonly=True)
    volume = fields.Float('Volume', readonly=True)
    order_id = fields.Many2one('purchase.order', 'Order', readonly=True)
    untaxed_total = fields.Monetary('Untaxed Total', readonly=True)
    qty_ordered = fields.Float('Qty Ordered', readonly=True)
    qty_received = fields.Float('Qty Received', readonly=True)
    qty_billed = fields.Float('Qty Billed', readonly=True)
    qty_to_be_billed = fields.Float('Qty to be Billed', readonly=True)

    @property
    def _table_query(self) -> SQL:
        today = fields.Date.today()
        query = self.env['purchase.order.line'].sudo().with_context(date_to=today)._search([('display_type', '=', False)])
        query.groupby = SQL(", ").join(self._groupby_list(query.table))
        return query.subselect(*self._select_list(query.table))

    def _select_list(self, table: TableSQL):
        uom_ratio = SQL("(COALESCE(%s, 1) / NULLIF(COALESCE(%s, 1), 0.0))", table.uom_id.factor, table.product_id.uom_id.factor)
        return [
            SQL("%s AS order_id", table.order_id.id),
            SQL("MIN(%s) AS id", table.id),
            table.order_id.date_order,
            table.order_id.state,
            table.order_id.date_approve,
            table.order_id.dest_address_id,
            table.order_id.partner_id,
            table.order_id.user_id,
            table.order_id.company_id,
            table.order_id.fiscal_position_id,
            SQL("%s AS product_id", table.product_id.id),
            table.product_id.product_tmpl_id,
            SQL("%s AS category_id", table.product_id.product_tmpl_id.categ_id),
            table.order_id.company_id.currency_id,
            table.product_id.product_tmpl_id.uom_id,
            SQL("EXTRACT(epoch FROM AGE(%s, %s))/(24*60*60)::decimal(16,2) AS delay", table.order_id.date_approve, table.order_id.date_order),
            SQL("EXTRACT(epoch FROM AGE(%s, %s))/(24*60*60)::decimal(16,2) AS delay_pass", table.date_planned, table.order_id.date_order),
            SQL("COUNT(*) AS nbr_lines"),
            SQL("SUM(%s / COALESCE(%s, 1.0))::decimal(16,2) * %s as price_total", table.price_total, table.order_id.currency_rate, table.consolidation_rate),
            SQL(
                "(SUM(%s * %s / COALESCE(%s, 1.0))/NULLIF(SUM(%s * %s),0.0))::decimal(16,2) * %s as price_average",
                table.product_qty, table.price_unit, table.order_id.currency_rate, table.product_qty, uom_ratio, table.consolidation_rate,
            ),
            table.order_id.partner_id.country_id,
            table.order_id.partner_id.commercial_partner_id,
            SQL("SUM(%s * %s * %s) AS weight", table.product_id.weight, table.product_qty, uom_ratio),
            SQL("SUM(%s * %s * %s) AS volume", table.product_id.volume, table.product_qty, uom_ratio),
            SQL("SUM(%s / COALESCE(%s, 1.0))::decimal(16,2) * %s as untaxed_total", table.price_subtotal, table.order_id.currency_rate, table.consolidation_rate),
            SQL("SUM(%s * %s) AS qty_ordered", table.product_qty, uom_ratio),
            SQL("SUM(%s * %s) AS qty_received", table.qty_received, uom_ratio),
            SQL("SUM(%s * %s) AS qty_billed", table.qty_invoiced, uom_ratio),
            SQL(
                """CASE WHEN %s = 'purchase'
                    THEN SUM(%s * %s) - SUM(%s * %s)
                    ELSE SUM(%s * %s) - SUM(%s * %s)
                   END AS qty_to_be_billed""",
                table.product_id.product_tmpl_id.purchase_method,
                table.product_qty, uom_ratio, table.qty_invoiced, uom_ratio,
                table.qty_received, uom_ratio, table.qty_invoiced, uom_ratio,
            ),
        ]

    def _groupby_list(self, table: TableSQL):
        return [
            table.price_unit,
            table.date_planned,
            table.order_id.id,
            table.order_id.company_id.id,
            table.order_id.partner_id.id,
            table.product_id.id,
            table.product_id.product_tmpl_id.id,
            table.product_id.product_tmpl_id.uom_id.id,
            table.uom_id.id,
        ]

    def _read_group_select(self, table, aggregate_spec: str) -> SQL:
        """ This override allows us to correctly calculate the average price of products. """
        if aggregate_spec != 'price_average:avg':
            return super()._read_group_select(table, aggregate_spec)
        return SQL(
            'SUM(%(f_price)s * %(f_qty)s) / NULLIF(SUM(%(f_qty)s), 0.0)',
            f_price=table.price_average,
            f_qty=table.qty_ordered,
        )

    def action_open_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'views': [(False, 'form')],
        }
