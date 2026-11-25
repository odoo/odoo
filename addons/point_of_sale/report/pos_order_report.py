# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.tools import SQL


class ReportPosOrder(models.Model):
    _name = 'report.pos.order'
    _description = "Point of Sale Orders Report"
    _auto = False
    _order = 'date desc, id desc'
    _rec_name = 'order_id'

    date = fields.Datetime(string='Order Date', readonly=True)
    order_id = fields.Many2one('pos.order', string='Order', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    state = fields.Selection(
        [('draft', 'New'), ('paid', 'Paid'), ('done', 'Posted'), ('cancel', 'Cancelled')],
        string='Status', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    price_total = fields.Monetary(string='Total Price', readonly=True)
    price_sub_total = fields.Monetary(string='Subtotal w/o discount', readonly=True)
    price_subtotal_excl = fields.Monetary(string='Subtotal w/o Tax', readonly=True)
    total_discount = fields.Monetary(string='Total Discount', readonly=True)
    average_price = fields.Monetary(string='Average Price', readonly=True, aggregator="avg")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    nbr_lines = fields.Integer(string='Sale Line Count', readonly=True)
    product_qty = fields.Integer(string='Product Quantity', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    delay_validation = fields.Integer(string='Delay Validation', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    pos_categ_id = fields.Many2one('pos.category', string='Point of Sale Category', readonly=True)
    invoiced = fields.Boolean(readonly=True)
    config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    margin = fields.Monetary(string='Margin', readonly=True)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', readonly=True)
    preset_id = fields.Many2one('pos.preset', string='Preset', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)

    def _select(self):
        return SQL("""
            -- Each order line is reported once per payment method used by its order, its
            -- amounts prorated by the share that method represents in the order.
            WITH payment_by_method AS (
                SELECT
                    pay.pos_order_id,
                    pay.payment_method_id,
                    SUM(pay.amount) AS amount
                FROM pos_payment pay
                GROUP BY pay.pos_order_id, pay.payment_method_id
            ),
            -- The share of each payment method in its order, and the rank of the method in
            -- the order: 0 is the main method, the one that paid the largest part (in
            -- absolute value, so that refunds are ranked like sales).
            payment_share AS (
                SELECT
                    pos_order_id,
                    payment_method_id,
                    CASE
                        WHEN SUM(amount) OVER (PARTITION BY pos_order_id) = 0
                            THEN 1.0 / COUNT(*) OVER (PARTITION BY pos_order_id)
                        ELSE amount / SUM(amount) OVER (PARTITION BY pos_order_id)
                    END AS share,
                    ROW_NUMBER() OVER (
                        PARTITION BY pos_order_id ORDER BY ABS(amount) DESC, payment_method_id
                    ) - 1 AS method_rank
                FROM payment_by_method
            ),
            first_pos_category AS (
                SELECT
                    pt.id AS product_template_id,
                    (array_agg(pc.id))[1] AS id
                FROM product_template pt
                LEFT JOIN pos_category_product_template_rel pcpt ON (pt.id = pcpt.product_template_id)
                LEFT JOIN pos_category pc ON (pcpt.pos_category_id = pc.id)
                GROUP BY pt.id
            )
            SELECT
                l.id::bigint * 1000 + COALESCE(pay.method_rank, 0) AS id, -- stable: one id per line and method
                CASE WHEN COALESCE(pay.method_rank, 0) = 0 THEN 1 ELSE 0 END AS nbr_lines, -- a line is counted on one method only
                s.date_order AS date,
                ROUND((SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal) * COALESCE(pay.share, 1.0)) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places) AS price_subtotal_excl,
                CASE WHEN COALESCE(pay.method_rank, 0) = 0 THEN l.qty ELSE 0 END AS product_qty,
                (l.qty * l.price_unit * COALESCE(pay.share, 1.0)) / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS price_sub_total,
                ROUND((SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal_incl) * COALESCE(pay.share, 1.0)) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places) AS price_total,
                (l.qty * l.price_unit * COALESCE(pay.share, 1.0)) * (l.discount / 100) / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS total_discount,
                CASE
                    WHEN COALESCE(pay.method_rank, 0) > 0 OR l.qty * u.factor = 0 THEN NULL
                    ELSE (l.qty*l.price_unit / COALESCE(NULLIF(s.currency_rate, 0), 1.0))/(l.qty * u.factor)::decimal
                END AS average_price,
                CASE WHEN COALESCE(pay.method_rank, 0) = 0
                    THEN cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)
                    ELSE 0
                END AS delay_validation,
                s.id as order_id,
                s.partner_id AS partner_id,
                s.state AS state,
                s.user_id AS user_id,
                s.company_id AS company_id,
                co.currency_id AS currency_id,
                s.sale_journal AS journal_id,
                l.product_id AS product_id,
                pt.categ_id AS product_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                s.pricelist_id,
                s.session_id,
                s.preset_id,
                s.account_move IS NOT NULL AS invoiced,
                (((SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal)) - COALESCE(l.total_cost,0)) * COALESCE(pay.share, 1.0)) / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS margin,
                pay.payment_method_id AS payment_method_id,
                fpc.id AS pos_categ_id

        """)

    def _from(self):
        return SQL("""
            FROM pos_order_line AS l
                INNER JOIN pos_order s ON (s.id=l.order_id)
                LEFT JOIN product_product p ON (l.product_id=p.id)
                LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                LEFT JOIN res_company co ON (s.company_id=co.id)
                LEFT JOIN res_currency cu ON (co.currency_id=cu.id)
                LEFT JOIN payment_share pay ON (pay.pos_order_id=s.id)
                LEFT JOIN first_pos_category fpc ON (pt.id = fpc.product_template_id)
        """)

    def _group_by(self):
        return SQL()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
            )
        """, SQL.identifier(self._table), self._select(), self._from())
        )
