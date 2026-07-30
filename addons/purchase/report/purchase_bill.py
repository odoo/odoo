# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models, tools, _
from odoo.tools import formatLang

class PurchaseBillUnion(models.Model):
    _name = 'purchase.bill.union'
    _auto = False
    _description = 'Purchases & Bills Union'
    _order = "date desc, name desc"
    _rec_names_search = ['name', 'reference']

    name = fields.Char(string='Reference', readonly=True)
    reference = fields.Char(string='Source', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'purchase_bill_union')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_bill_union AS (
                SELECT
                    id, name, ref as reference, partner_id, date, amount_untaxed as amount, currency_id, company_id,
                    id as vendor_bill_id, NULL as purchase_order_id
                FROM account_move
                WHERE
                    move_type='in_invoice' and state = 'posted'
            UNION
                SELECT
                    -id, name, partner_ref as reference, partner_id, date_order::date as date, amount_untaxed as amount, currency_id, company_id,
                    NULL as vendor_bill_id, id as purchase_order_id
                FROM purchase_order
                WHERE
                    state in ('purchase', 'done') AND
                    invoice_status in ('to invoice', 'no')
            )""")

    @api.depends('currency_id', 'reference', 'amount', 'purchase_order_id')
    def _compute_display_name(self):
        po_amount = defaultdict(float)
        for _line, order, subtotal, qty, price_unit, qty_to_invoice in self.env['purchase.order.line']._read_group(
            [('qty_to_invoice', '!=', 0),
             ('price_unit', '!=', 0),
             ('display_type', '=', False),
             ('order_id', 'in', self.purchase_order_id.filtered(lambda x: x.invoice_status == 'to invoice').ids)],
            ['id', 'order_id'], ['price_subtotal:sum', 'product_qty:sum', 'price_unit:sum', 'qty_to_invoice:sum']
        ):
            po_amount[order] += qty_to_invoice * (subtotal / qty if qty else price_unit)

        for doc in self:
            name = doc.name or ''
            if doc.reference:
                name += ' - ' + doc.reference
            amount = doc.amount
            name += ': ' + formatLang(self.env, amount, currency_obj=doc.currency_id)
            if doc.purchase_order_id:
                if doc.purchase_order_id.invoice_status == 'no':
                    name += _(' - Nothing to Invoice')
                elif doc.purchase_order_id.invoice_status == 'to invoice':
                    to_invoice = po_amount.get(doc.purchase_order_id, 0)
                    name += _(' - To invoice: %(amount)s', amount=formatLang(self.env, to_invoice, currency_obj=doc.currency_id))
            doc.display_name = name
