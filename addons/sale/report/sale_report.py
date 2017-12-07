# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _name = "sale.report"
    _description = "Sales Orders Statistics"
    _auto = False

    name = fields.Char('Order Reference', readonly=True)
    confirmation_date = fields.Datetime('Confirmation Date', readonly=True)
    product_uom = fields.Many2one('product.uom', 'Unit of Measure', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    date_order = fields.Datetime(string='Date Order', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    price_total = fields.Float('Total', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    country_id = fields.Many2one('res.country', 'Partner Country', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Commercial Entity', readonly=True)
    price_subtotal = fields.Float(string='Price Subtotal', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Channel', readonly=True)
    product_uom_qty = fields.Float('Product Quantity', readonly=True)
    qty_delivered = fields.Float('Qty Delivered', readonly=True)
    qty_to_invoice = fields.Float('Qty To Invoice', readonly=True)
    qty_invoiced = fields.Float('Qty Invoiced', readonly=True)
    amt_to_invoice = fields.Float('Amount To Invoice', readonly=True)
    amt_invoiced = fields.Float('Amount Invoiced', readonly=True)
    nbr = fields.Integer('# of Lines', readonly=True)
    weight = fields.Float('Gross Weight', readonly=True)
    volume = fields.Float('Volume', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True)

    def _select(self):
        select_str = """
            WITH currency_rate as (%s)
                SELECT sol.id AS id,
                    so.name AS name,
                    so.partner_id AS partner_id,
                    sol.product_id AS product_id,
                    pt.uom_id AS product_uom,
                    pro.product_tmpl_id AS product_tmpl_id,
                    so.date_order AS date_order,
                    so.confirmation_date AS confirmation_date,
                    so.user_id AS user_id,
                    pt.categ_id AS categ_id,
                    so.company_id AS company_id,
                    extract(epoch from avg(date_trunc('day',so.date_order)-date_trunc('day',so.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    sol.price_total AS price_total,
                    so.pricelist_id AS pricelist_id,
                    rp.country_id AS country_id,
                    sol.price_subtotal / COALESCE (cr.rate, 1.0) AS price_subtotal,
                    so.state AS state,
                    sum(sol.product_uom_qty / u.factor * u2.factor) AS product_uom_qty,
                    sum(sol.qty_delivered / u.factor * u2.factor) AS qty_delivered,
                    sum(sol.qty_invoiced / u.factor * u2.factor) AS qty_invoiced,
                    sum(sol.qty_to_invoice / u.factor * u2.factor) AS qty_to_invoice,
                    sum(sol.amt_to_invoice / COALESCE(cr.rate, 1.0)) AS amt_to_invoice,
                    sum(sol.amt_invoiced / COALESCE(cr.rate, 1.0)) AS amt_invoiced,
                    count(*) AS nbr,
                    sum(pro.weight * sol.product_uom_qty / u.factor * u2.factor) AS weight,
                    sum(pro.volume * sol.product_uom_qty / u.factor * u2.factor) AS volume,
                    so.analytic_account_id AS analytic_account_id,
                    so.team_id AS team_id,
                    rp.commercial_partner_id AS commercial_partner_id,
                    NULL AS margin
        """ % self.env['res.currency']._select_companies_rates()
        return select_str

    def _from_str(self):
        from_str = """
        FROM
            sale_order_line sol
                JOIN sale_order so ON (sol.order_id = so.id)
                LEFT JOIN product_product pro ON (sol.product_id = pro.id)
                JOIN res_partner rp ON (so.partner_id = rp.id)
                LEFT JOIN product_template pt ON (pro.product_tmpl_id = pt.id)
                LEFT JOIN product_pricelist pp ON (so.pricelist_id = pp.id)
                LEFT JOIN currency_rate cr ON (cr.currency_id = pp.currency_id AND
                    cr.company_id = so.company_id AND
                    cr.date_start <= COALESCE(so.date_order, now()) AND
                    (cr.date_end IS NULL OR cr.date_end > COALESCE(so.date_order, now())))
                LEFT JOIN product_uom u on (u.id=sol.product_uom)
                LEFT JOIN product_uom u2 on (u2.id=pt.uom_id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY sol.id,
                    so.name,
                    so.partner_id,
                    sol.product_id,
                    sol.order_id,
                    pt.uom_id,
                    pro.product_tmpl_id,
                    so.date_order,
                    so.confirmation_date,
                    so.user_id,
                    pt.categ_id,
                    so.company_id,
                    sol.price_total,
                    so.pricelist_id,
                    rp.country_id,
                    sol.price_subtotal / COALESCE (cr.rate, 1.0),
                    so.state,
                    (sol.product_uom_qty / u.factor * u2.factor),
                    so.analytic_account_id,
                    so.team_id,
                    rp.country_id,
                    rp.commercial_partner_id
        """
        return group_by_str

    def _from(self):
        return """(%s)""" % (self._select() + self._from_str() + self._group_by())

    def get_main_request_select(self):
        return """
            CREATE or REPLACE VIEW %s AS
                SELECT id AS id,
                    name,
                    partner_id,
                    product_id,
                    product_tmpl_id,
                    date_order,
                    confirmation_date,
                    user_id,
                    product_uom,
                    categ_id,
                    company_id,
                    price_total,
                    pricelist_id,
                    analytic_account_id,
                    country_id,
                    team_id,
                    price_subtotal,
                    state,
                    product_uom_qty,
                    qty_delivered,
                    qty_invoiced,
                    qty_to_invoice,
                    amt_to_invoice,
                    amt_invoiced,
                    nbr,
                    weight,
                    volume,
                    margin,
                    commercial_partner_id """ % (self._table)

    def get_main_request_from(self):
        return """ FROM %s
                AS foo""" % (self._from())

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(self.get_main_request_select() + self.get_main_request_from())


class SaleOrderReportProforma(models.AbstractModel):
    _name = 'report.sale.report_saleproforma'

    @api.multi
    def get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'sale.order',
            'docs': docs,
            'proforma': True
        }
