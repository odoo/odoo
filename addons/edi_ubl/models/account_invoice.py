# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    ubl_type_code = fields.Char(compute='_compute_ubl_type_code')

    @api.multi
    @api.depends('type')
    def _compute_ubl_type_code(self):
        for record in self:
            if record.type == 'out_invoice':
                record.ubl_type_code = '380'
            elif record.type == 'out_refund':
                record.ubl_type_code = '381'

    def get_account_tax(self, tax_line):
        AccountTax = item.env['account.tax']
        taxes = AccountTax.search([('base_code_id', '=', item_line.base_code_id.id)])[0]
        return taxes[0]

    def get_res_taxes(self, item_line, partner):
        line_price = item_line.price_unit * (1 - (item_line.discount or 0.0) / 100.0)
        res_taxes = item_line.invoice_line_tax_ids.compute_all(
            line_price, quantity=item_line.quantity, product=item_line.product_id, partner=partner)
        return res_taxes


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    ubl_line_price = fields.Float(compute='_compute_ubl_line_price')
    ubl_seller_code = fields.Char(compute='_compute_ubl_seller_code')
    ubl_product_name = fields.Char(compute='_compute_ubl_product_name')

    @api.multi
    @api.depends('price_unit', 'discount')
    def _compute_ubl_line_price(self):
        for record in self:
            record.ubl_line_price = \
                record.price_unit * (1 - (record.discount or 0.0) / 100.0)

    @api.multi
    @api.depends('product_id')
    def _compute_ubl_seller_code(self):
        for record in self:
            record.ubl_seller_code = record.product_id.default_code

    @api.multi
    @api.depends('product_id')
    def _compute_ubl_product_name(self):
        for record in self:
            variants = [variant.name for variant in record.product_id.attribute_value_ids]
            if variants:
                record.ubl_product_name = "%s (%s)" % (record.product_id.name, ', '.join(variants))
            else:
                record.ubl_product_name = record.product_id.name

    @api.multi
    def ubl_get_res_taxes(self):
        self.ensure_one()
        partner_id = self.invoice_id.partner_id
        res_taxes = self.invoice_line_tax_ids.compute_all(
            self.ubl_line_price, 
            quantity=self.quantity, 
            product=self.product_id, 
            partner=partner_id)
        return res_taxes

