# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class PurchaseBillUnion(models.Model):
    _name = 'purchase.bill.union'
    _auto = False
    _description = 'Bills & Purchases'
    _order = "date desc, purchase_order_id desc, vendor_bill_id desc"

    name = fields.Char(string='Reference', readonly=True)
    reference = fields.Char(string='Source', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    vendor_bill_id = fields.Many2one('account.invoice', string='Vendor Bill', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'purchase_bill_union')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_bill_union AS (
                SELECT
                    id, number as name, reference, partner_id, date, amount_untaxed as amount, currency_id, company_id,
                    id as vendor_bill_id, NULL as purchase_order_id
                FROM account_invoice
                WHERE
                    type='in_invoice' and state in ('open','paid','cancel')
            UNION
                SELECT
                    -id, name, partner_ref, partner_id, date_order as date, amount_untaxed as amount, currency_id, company_id,
                    NULL as vendor_bill_id, id as purchase_order_id
                FROM purchase_order
                WHERE
                    state = 'purchase' AND
                    invoice_status = 'to invoice'
            )""")

    def name_get(self):
        result = []
        lang_code = self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)])
        for doc in self:
            name = doc.name or ''
            if doc.reference:
                name += ' - ' + doc.reference
            amount = doc.amount
            if doc.purchase_order_id and doc.purchase_order_id.invoice_status == 'no':
                amount = 0.0
            amt = lang.format('%.' + str(doc.currency_id.decimal_places) + 'f', amount, True, True)
            if doc.currency_id.position == 'before':
                name += ': {}{}'.format(doc.currency_id.symbol, amt)
            else:
                name += ': {}{}'.format(amt, doc.currency_id.symbol)
            result.append((doc.id, name))
        return result


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    vendor_bill_purchase_id = fields.Many2one(
        comodel_name='purchase.bill.union',
        string='Auto-Complete'
    )

    @api.onchange('vendor_bill_purchase_id')
    def _onchange_bill_purchase_order(self):
        if not self.vendor_bill_purchase_id:
            return {}
        self.purchase_id = self.vendor_bill_purchase_id.purchase_order_id
        self.vendor_bill_id = self.vendor_bill_purchase_id.vendor_bill_id
        self.vendor_bill_purchase_id = False
        return {}
