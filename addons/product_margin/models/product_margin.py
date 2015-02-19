# -*- coding: utf-8 -*-

from datetime import date

from openerp import api, fields, models


class Product(models.Model):
    _inherit = "product.product"

    @api.one
    def _product_margin(self):
        date_from = self.env.context.get('from_date', fields.Date.to_string(date(date.today().year, 1, 1)))
        date_to = self.env.context.get('to_date', fields.Date.to_string(date(date.today().year, 12, 31)))
        invoice_state = self.env.context.get('invoice_state', 'open_paid')
        self.date_from = date_from
        self.date_to = date_to
        self.invoice_state = invoice_state
        states = ()
        if invoice_state == 'paid':
            states = ('paid',)
        elif invoice_state == 'open_paid':
            states = ('open', 'paid')
        elif invoice_state == 'draft_open_paid':
            states = ('draft', 'open', 'paid')
        if "force_company" in self.env.context:
            company_id = self.env.context['force_company']
        else:
            company_id = self.env.user.company_id.id

        #Cost price is calculated afterwards as it is a property
        sqlstr = """SELECT
                i.type,
                SUM(l.price_unit * l.quantity)/SUM(nullif(l.quantity * pu.factor / pu2.factor,0)) AS avg_unit_price,
                SUM(l.quantity * pu.factor / pu2.factor) AS num_qty,
                SUM(l.quantity * (l.price_subtotal/(nullif(l.quantity,0)))) AS total,
                SUM(l.quantity * pu.factor * pt.list_price / pu2.factor) AS sale_expected
            FROM account_invoice_line l
            LEFT JOIN account_invoice i ON (l.invoice_id = i.id)
            LEFT JOIN product_product product ON (product.id=l.product_id)
            LEFT JOIN product_template pt ON (pt.id = l.product_id)
                LEFT JOIN product_uom pu ON (pt.uom_id = pu.id)
                LEFT JOIN product_uom pu2 ON (l.uos_id = pu2.id)
            WHERE l.product_id = %s AND i.state IN %s AND (i.date_invoice IS NULL OR (i.date_invoice>=%s AND i.date_invoice<=%s AND i.company_id=%s))
            GROUP BY i.type"""
        self.env.cr.execute(sqlstr, (self.id, states, date_from, date_to, company_id))
        result = self.env.cr.fetchall()
        Product = self.env['product.product']
        product = Product.with_context(force_company=company_id).browse(self.id)

        for res in result:
            if res[0] == 'out_invoice' or res[0] == 'in_refund':
                self.sale_avg_price = res[1] and res[1] or 0.0
                self.sale_num_invoiced = res[2] and res[2] or 0.0
                self.turnover = res[3] and res[3] or 0.0
                self.sale_expected = res[4] and res[4] or 0.0
                self.sales_gap = self.sale_expected - self.turnover
            else:
                self.purchase_avg_price = res[1] and res[1] or 0.0
                self.purchase_num_invoiced = res[2] and res[2] or 0.0
                self.total_cost = res[3] and res[3] or 0.0
                self.normal_cost = product.standard_price * self.purchase_num_invoiced
                self.purchase_gap = self.normal_cost - self.total_cost

            self.total_margin = self.turnover - self.total_cost
            self.expected_margin = self.sale_expected - self.normal_cost
            self.total_margin_rate = self.turnover and self.total_margin * 100 / self.turnover or 0.0
            self.expected_margin_rate = self.sale_expected and self.expected_margin * 100 / self.sale_expected or 0.0

    date_from = fields.Date(compute='_product_margin', string='Margin Date From')
    date_to = fields.Date(compute='_product_margin', string='Margin Date To')
    invoice_state = fields.Selection(compute='_product_margin', selection=[('paid', 'Paid'), ('open_paid', 'Open and Paid'),
                                    ('draft_open_paid', 'Draft, Open and Paid')], readonly=True)
    sale_avg_price = fields.Float(compute='_product_margin', string='Avg. Unit Price', help="Avg. Price in Customer Invoices.")
    purchase_avg_price = fields.Float(compute='_product_margin', string='Avg. Unit Price', help="Avg. Price in Supplier Invoices ")
    sale_num_invoiced = fields.Float(compute='_product_margin', string='# Invoiced in Sale', help="Sum of Quantity in Customer Invoices")
    purchase_num_invoiced = fields.Float(compute='_product_margin', string='# Invoiced in Purchase', multi='product_margin', help="Sum of Quantity in Supplier Invoices")
    sales_gap = fields.Float(compute='_product_margin', help="Expected Sale - Turn Over")
    purchase_gap = fields.Float(compute='_product_margin', help="Normal Cost - Total Cost")
    turnover = fields.Float(compute='_product_margin', help="Sum of Multiplication of Invoice price and quantity of Customer Invoices")
    total_cost = fields.Float(compute='_product_margin', help="Sum of Multiplication of Invoice price and quantity of Supplier Invoices ")
    sale_expected = fields.Float(compute='_product_margin', string='Expected Sale', help="Sum of Multiplication of Sale Catalog price and quantity of Customer Invoices")
    normal_cost = fields.Float(compute='_product_margin', help="Sum of Multiplication of Cost price and quantity of Supplier Invoices")
    total_margin = fields.Float(compute='_product_margin', help="Turnover - Standard price")
    expected_margin = fields.Float(compute='_product_margin', help="Expected Sale - Normal Cost")
    total_margin_rate = fields.Float(compute='_product_margin', string='Total Margin Rate(%)', help="Total margin * 100 / Turnover")
    expected_margin_rate = fields.Float(compute='_product_margin', string='Expected Margin (%)', help="Expected margin * 100 / Expected Sale")
