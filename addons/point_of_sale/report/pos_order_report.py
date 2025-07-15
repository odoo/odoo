# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ReportPosOrder(models.Model):
    _name = 'report.pos.order'
    _description = "Point of Sale Orders Report"
    _auto = False
    _order = 'date desc'
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
    price_total = fields.Float(string='Total Price', readonly=True)
    price_sub_total = fields.Float(string='Subtotal w/o discount', readonly=True)
    price_subtotal_excl = fields.Float(string='Subtotal w/o Tax', readonly=True)
    total_discount = fields.Float(string='Total Discount', readonly=True)
    average_price = fields.Float(string='Average Price', readonly=True, aggregator="avg")
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
    margin = fields.Float(string='Margin', readonly=True)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', readonly=True)

    def _select(self):
        return """
            -- The purpose of this CTE is to map each "pos_order_line" to the "payment_method_id" corresponding to its "pos_order"
            -- considering we always show the first "payment_method_id"
            WITH payment_method_by_order_line AS (
                SELECT
                    pol.id AS pos_order_line_id,
                    pm.pos_order_id as pos_order_id,
                    (array_agg(pm.payment_method_id ORDER BY pm.id ASC))[1] AS payment_method_id
                FROM pos_order_line pol
                LEFT JOIN pos_order po ON (po.id = pol.order_id)
                LEFT JOIN pos_payment pm ON (pm.pos_order_id=po.id)
                GROUP BY pol.id, pm.pos_order_id
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
                l.id AS id,
                1 AS nbr_lines, -- number of lines in order line is always 1
                s.date_order AS date,
                ROUND((l.price_subtotal) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places) AS price_subtotal_excl,
                l.qty AS product_qty,
                l.qty * l.price_unit / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS price_sub_total,
                ROUND((l.price_subtotal_incl) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places) AS price_total,
                (l.qty * l.price_unit) * (l.discount / 100) / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS total_discount,
                CASE
                    WHEN l.qty * u.factor = 0 THEN NULL
                    ELSE (l.qty*l.price_unit / COALESCE(NULLIF(s.currency_rate, 0), 1.0))/(l.qty * u.factor)::decimal
                END AS average_price,
                cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT) AS delay_validation,
                s.id as order_id,
                s.partner_id AS partner_id,
                s.state AS state,
                s.user_id AS user_id,
                s.company_id AS company_id,
                s.sale_journal AS journal_id,
                l.product_id AS product_id,
                pt.categ_id AS product_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                s.pricelist_id,
                s.session_id,
                s.account_move IS NOT NULL AS invoiced,
                l.price_subtotal - COALESCE(l.total_cost,0) / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS margin,
                pm.payment_method_id AS payment_method_id,
                fpc.id AS pos_categ_id

        """

    def _from(self):
        return """
            FROM pos_order_line AS l
                INNER JOIN pos_order s ON (s.id=l.order_id)
                LEFT JOIN product_product p ON (l.product_id=p.id)
                LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                LEFT JOIN res_company co ON (s.company_id=co.id)
                LEFT JOIN res_currency cu ON (co.currency_id=cu.id)
                LEFT JOIN payment_method_by_order_line pm ON (pm.pos_order_line_id=l.id)
                LEFT JOIN pos_payment_method ppm ON (pm.payment_method_id=ppm.id)
                LEFT JOIN first_pos_category fpc ON (pt.id = fpc.product_template_id)
        """

    def _group_by(self):
        return ""

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
            )
        """ % (self._table, self._select(), self._from())
        )
