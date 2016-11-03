# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    ubl_customer = fields.Many2one(related='partner_id')
    ubl_supplier = fields.Many2one(related='company_id.partner_id')
    ubl_com_customer = fields.Many2one(related='partner_id.commercial_partner_id')
    ubl_com_supplier = fields.Many2one(related='company_id.partner_id.commercial_partner_id')
    ubl_id = fields.Char(related='number', readonly=True)
    ubl_issue_date = fields.Date(related='date_invoice', readonly=True)
    ubl_type_code = fields.Char(compute='_compute_ubl_type_code')
    ubl_supplier_phone = fields.Char(compute='_compute_ubl_supplier_phone')
    ubl_supplier_fax = fields.Char(compute='_compute_ubl_supplier_fax')
    ubl_supplier_email = fields.Char(compute='_compute_ubl_supplier_email')
    ubl_customer_phone = fields.Char(compute='_compute_ubl_customer_phone')
    ubl_customer_fax = fields.Char(compute='_compute_ubl_customer_fax')
    ubl_customer_email = fields.Char(compute='_compute_ubl_customer_email')
    ubl_amount_untaxed_format = fields.Float(compute='_compute_ubl_amount_untaxed_format')
    ubl_amount_total_format = fields.Float(compute='_compute_ubl_amount_total_format')
    ubl_amount_prepaid_format = fields.Float(compute='_compute_ubl_amount_prepaid_format')
    ubl_residual_format = fields.Float(compute='_compute_ubl_residual_format')

    @api.multi
    @api.depends('type')
    def _compute_ubl_type_code(self):
        for record in self:
            if record.type == 'out_invoice':
                record.ubl_type_code = '380'
            elif record.type == 'out_refund':
                record.ubl_type_code = '381'

    @api.multi
    @api.depends('ubl_supplier', 'ubl_com_supplier')
    def _compute_ubl_supplier_phone(self):
        for record in self:
            record.ubl_supplier_phone = \
                record.ubl_supplier.phone or \
                record.ubl_com_supplier.phone

    @api.multi
    @api.depends('ubl_supplier', 'ubl_com_supplier')
    def _compute_ubl_supplier_fax(self):
        for record in self:
            record.ubl_supplier_fax = \
                record.ubl_supplier.fax or \
                record.ubl_com_supplier.fax

    @api.multi
    @api.depends('ubl_supplier', 'ubl_com_supplier')
    def _compute_ubl_supplier_email(self):
        for record in self:
            record.ubl_supplier_email = \
                record.ubl_supplier.email or \
                record.ubl_com_supplier.email

    @api.multi
    @api.depends('ubl_customer', 'ubl_com_customer')
    def _compute_ubl_customer_phone(self):
        for record in self:
            record.ubl_customer_phone = \
                record.ubl_customer.phone or \
                record.ubl_com_customer.phone

    @api.multi
    @api.depends('ubl_customer', 'ubl_com_customer')
    def _compute_ubl_customer_fax(self):
        for record in self:
            record.ubl_customer_fax = \
                record.ubl_customer.fax or \
                record.ubl_com_customer.fax

    @api.multi
    @api.depends('ubl_customer', 'ubl_com_customer')
    def _compute_ubl_customer_email(self):
        for record in self:
            record.ubl_customer_email = \
                record.ubl_customer.email or \
                record.ubl_com_customer.email

    @api.multi
    @api.depends('amount_untaxed')
    def _compute_ubl_amount_untaxed_format(self):
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        for record in self:
            record.ubl_amount_untaxed_format = \
                '%0.*f' % (precision_digits, record.amount_untaxed)

    @api.multi
    @api.depends('amount_total')
    def _compute_ubl_amount_total_format(self):
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        for record in self:
            record.ubl_amount_total_format = \
                '%0.*f' % (precision_digits, record.amount_total)

    @api.multi
    @api.depends('amount_total', 'ubl_residual_format')
    def _compute_ubl_amount_prepaid_format(self):
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        for record in self:
            amount_prepaid = record.amount_total - record.ubl_residual_format
            record.ubl_amount_prepaid_format = \
                '%0.*f' % (precision_digits, amount_prepaid)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    ubl_price_subtotal = fields.Float(compute='_compute_ubl_price_subtotal')
    ubl_price = fields.Float(compute='_compute_ubl_line_price')
    ubl_total_tax = fields.Float(compute='_compute_taxes_informations')
    ubl_base_tax = fields.Float() # computed inside _compute_taxes_informations
    ubl_total_included = fields.Float() # computed inside _compute_taxes_informations
    ubl_total_excluded = fields.Float() # computed inside _compute_taxes_informations
    ubl_seller_code = fields.Char(compute='_compute_ubl_seller_code')
    ubl_product_name = fields.Char(compute='_compute_ubl_product_name')
    ubl_inline_name = fields.Char(compute='_compute_ubl_inline_name')

    @api.multi
    @api.depends('price_subtotal')
    def _compute_ubl_price_subtotal(self):
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        for record in self:
            record.ubl_price_subtotal = \
                '%0.*f' % (precision_digits, record.price_subtotal)

    @api.multi
    @api.depends('price_unit', 'discount')
    def _compute_ubl_line_price(self):
        for record in self:
            record.ubl_price = \
                record.price_unit * (1 - (record.discount or 0.0) / 100.0)

    @api.multi
    @api.depends('invoice_id', 'ubl_price')
    def _compute_taxes_informations(self):
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        for record in self:
            partner_id = record.invoice_id.partner_id
            res_taxes = record.invoice_line_tax_ids.compute_all(
                record.ubl_price, 
                quantity=record.quantity, 
                product=record.product_id, 
                partner=partner_id)
            record.ubl_total_included = tools.float_round(
                    res_taxes['total_included'], 
                    precision_digits=precision_digits)
            record.ubl_total_excluded = tools.float_round(
                    res_taxes['total_excluded'], 
                    precision_digits=precision_digits)
            record.ubl_total_tax = \
                record.ubl_total_included - record.ubl_total_excluded
            record.ubl_base_tax = res_taxes['base']

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
    @api.depends('name')
    def _compute_ubl_inline_name(self):
        for record in self:
            lines = map(lambda line: line.strip(), record.name.split('\n'))
            record.ubl_inline_name = ', '.join(lines)

    class AccountInvoiceTax(models.Model):
        _inherit = 'account.invoice.tax'

        ubl_tax_percent = fields.Float(compute='_compute_ubl_tax_percent')
        # ubl_account_tax = fields.Many2one(compute='_compute_ubl_account_tax')

        @api.multi
        @api.depends('amount')
        def _compute_ubl_tax_percent(self):
            for record in self:
                record.ubl_tax_percent = \
                    tools.float_round((record.amount / record.base) * 100, precision_digits=2)

        @api.multi
        @api.depends('base_code_id')
        def _compute_ubl_account_tax(self):
            for record in self:
                taxes = self.env['account.tax'].search([
                ('base_code_id', '=', record.base_code_id.id)])
                record.ubl_account_tax = taxes[0]