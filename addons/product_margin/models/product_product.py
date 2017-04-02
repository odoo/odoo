# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = "product.product"

    date_from = fields.Date(compute='_compute_product_margin_fields_values', string='Margin Date From')
    date_to = fields.Date(compute='_compute_product_margin_fields_values', string='Margin Date To')
    invoice_state = fields.Selection(compute='_compute_product_margin_fields_values',
        selection=[
            ('paid', 'Paid'),
            ('open_paid', 'Open and Paid'),
            ('draft_open_paid', 'Draft, Open and Paid')
        ], string='Invoice State', readonly=True)
    sale_avg_price = fields.Float(compute='_compute_product_margin_fields_values', string='Avg. Unit Price',
        help="Avg. Price in Customer Invoices.")
    purchase_avg_price = fields.Float(compute='_compute_product_margin_fields_values', string='Avg. Unit Price',
        help="Avg. Price in Vendor Bills ")
    sale_num_invoiced = fields.Float(compute='_compute_product_margin_fields_values', string='# Invoiced in Sale',
        help="Sum of Quantity in Customer Invoices")
    purchase_num_invoiced = fields.Float(compute='_compute_product_margin_fields_values', string='# Invoiced in Purchase',
        help="Sum of Quantity in Vendor Bills")
    sales_gap = fields.Float(compute='_compute_product_margin_fields_values', string='Sales Gap',
        help="Expected Sale - Turn Over")
    purchase_gap = fields.Float(compute='_compute_product_margin_fields_values', string='Purchase Gap',
        help="Normal Cost - Total Cost")
    turnover = fields.Float(compute='_compute_product_margin_fields_values', string='Turnover',
        help="Sum of Multiplication of Invoice price and quantity of Customer Invoices")
    total_cost = fields.Float(compute='_compute_product_margin_fields_values', string='Total Cost',
        help="Sum of Multiplication of Invoice price and quantity of Vendor Bills ")
    sale_expected = fields.Float(compute='_compute_product_margin_fields_values', string='Expected Sale',
        help="Sum of Multiplication of Sale Catalog price and quantity of Customer Invoices")
    normal_cost = fields.Float(compute='_compute_product_margin_fields_values', string='Normal Cost',
        help="Sum of Multiplication of Cost price and quantity of Vendor Bills")
    total_margin = fields.Float(compute='_compute_product_margin_fields_values', string='Total Margin',
        help="Turnover - Standard price")
    expected_margin = fields.Float(compute='_compute_product_margin_fields_values', string='Expected Margin',
        help="Expected Sale - Normal Cost")
    total_margin_rate = fields.Float(compute='_compute_product_margin_fields_values', string='Total Margin Rate(%)',
        help="Total margin * 100 / Turnover")
    expected_margin_rate = fields.Float(compute='_compute_product_margin_fields_values', string='Expected Margin (%)',
        help="Expected margin * 100 / Expected Sale")

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
            Inherit read_group to calculate the sum of the non-stored fields, as it is not automatically done anymore through the XML.
        """
        res = super(ProductProduct, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        fields_list = ['turnover', 'sale_avg_price', 'sale_purchase_price', 'sale_num_invoiced', 'purchase_num_invoiced',
                       'sales_gap', 'purchase_gap', 'total_cost', 'sale_expected', 'normal_cost', 'total_margin',
                       'expected_margin', 'total_margin_rate', 'expected_margin_rate']
        if any(x in fields for x in fields_list):
            # Calculate first for every product in which line it needs to be applied
            re_ind = 0
            prod_re = {}
            tot_products = self.browse([])
            for re in res:
                if re.get('__domain'):
                    products = self.search(re['__domain'])
                    tot_products |= products
                    for prod in products:
                        prod_re[prod.id] = re_ind
                re_ind += 1
            res_val = tot_products._compute_product_margin_fields_values(field_names=[x for x in fields if fields in fields_list])
            for key in res_val.keys():
                for l in res_val[key].keys():
                    re = res[prod_re[key]]
                    if re.get(l):
                        re[l] += res_val[key][l]
                    else:
                        re[l] = res_val[key][l]
        return res

    def _compute_product_margin_fields_values(self, field_names=None):
        res = {}
        if field_names is None:
            field_names = []
        for val in self:
            res[val.id] = {}
            date_from = self.env.context.get('date_from', time.strftime('%Y-01-01'))
            date_to = self.env.context.get('date_to', time.strftime('%Y-12-31'))
            invoice_state = self.env.context.get('invoice_state', 'open_paid')
            res[val.id]['date_from'] = date_from
            res[val.id]['date_to'] = date_to
            res[val.id]['invoice_state'] = invoice_state
            invoice_types = ()
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
            sqlstr = """
                select
                    sum(l.price_unit * l.quantity)/sum(nullif(l.quantity,0)) as avg_unit_price,
                    sum(l.quantity) as num_qty,
                    sum(l.quantity * (l.price_subtotal/(nullif(l.quantity,0)))) as total,
                    sum(l.quantity * pt.list_price) as sale_expected
                from account_invoice_line l
                left join account_invoice i on (l.invoice_id = i.id)
                left join product_product product on (product.id=l.product_id)
                left join product_template pt on (pt.id = product.product_tmpl_id)
                where l.product_id = %s and i.state in %s and i.type IN %s and (i.date_invoice IS NULL or (i.date_invoice>=%s and i.date_invoice<=%s and i.company_id=%s))
                """
            invoice_types = ('out_invoice', 'in_refund')
            self.env.cr.execute(sqlstr, (val.id, states, invoice_types, date_from, date_to, company_id))
            result = self.env.cr.fetchall()[0]
            res[val.id]['sale_avg_price'] = result[0] and result[0] or 0.0
            res[val.id]['sale_num_invoiced'] = result[1] and result[1] or 0.0
            res[val.id]['turnover'] = result[2] and result[2] or 0.0
            res[val.id]['sale_expected'] = result[3] and result[3] or 0.0
            res[val.id]['sales_gap'] = res[val.id]['sale_expected'] - res[val.id]['turnover']
            ctx = self.env.context.copy()
            ctx['force_company'] = company_id
            invoice_types = ('in_invoice', 'out_refund')
            self.env.cr.execute(sqlstr, (val.id, states, invoice_types, date_from, date_to, company_id))
            result = self.env.cr.fetchall()[0]
            res[val.id]['purchase_avg_price'] = result[0] and result[0] or 0.0
            res[val.id]['purchase_num_invoiced'] = result[1] and result[1] or 0.0
            res[val.id]['total_cost'] = result[2] and result[2] or 0.0
            res[val.id]['normal_cost'] = val.standard_price * res[val.id]['purchase_num_invoiced']
            res[val.id]['purchase_gap'] = res[val.id]['normal_cost'] - res[val.id]['total_cost']

            res[val.id]['total_margin'] = res[val.id]['turnover'] - res[val.id]['total_cost']
            res[val.id]['expected_margin'] = res[val.id]['sale_expected'] - res[val.id]['normal_cost']
            res[val.id]['total_margin_rate'] = res[val.id]['turnover'] and res[val.id]['total_margin'] * 100 / res[val.id]['turnover'] or 0.0
            res[val.id]['expected_margin_rate'] = res[val.id]['sale_expected'] and res[val.id]['expected_margin'] * 100 / res[val.id]['sale_expected'] or 0.0
            for k, v in res[val.id].items():
                setattr(val, k, v)
        return res
