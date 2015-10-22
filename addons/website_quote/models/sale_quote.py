# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
import odoo.addons.decimal_precision as dp

class SaleQuoteTemplate(models.Model):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"

    name = fields.Char(string='Quotation Template', required=True)
    website_description = fields.Html(string='Description', translate=True)
    quote_line = fields.One2many('sale.quote.line', 'quote_id', string='Quotation Template Lines', copy=True)
    note = fields.Text(string='Terms and conditions')
    options = fields.One2many('sale.quote.option', 'template_id', string='Optional Products Lines', copy=True)
    number_of_days = fields.Integer(string='Quotation Duration', help='Number of days for the validity date computation of the quotation')
    require_payment = fields.Selection([
        (0, 'Not mandatory on website quote validation'),
        (1, 'Immediate after website order validation')
    ], string='Payment', help="Require immediate payment by the customer when validating the order from the website quote")

    @api.multi
    def open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/template/%d' % self.id
        }

class SaleQuoteLine(models.Model):
    _name = "sale.quote.line"
    _description = "Quotation Template Lines"
    _order = 'sequence, id'

    sequence = fields.Integer(help="Gives the sequence order when displaying a list of sale quote lines.", default=10)
    quote_id = fields.Many2one('sale.quote.template', string='Quotation Template Reference', required=True, ondelete='cascade', index=True)
    name = fields.Text(string='Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True)
    website_description = fields.Html(related='product_id.product_tmpl_id.quote_description', string='Line Description', translate=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits_compute=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', digits_compute=dp.get_precision('Discount'))
    product_uom_qty = fields.Float(string='Quantity', required=True, digits_compute=dp.get_precision('Product UoS'), default=1)
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure ', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            domain = []
            product = self.product_id
            self.price_unit = product.lst_price
            self.website_description = product and (product.quote_description or product.website_description) or ''
            self.name = product.name + (product.description_sale and '\n' + product.description_sale or '')
            self.product_uom_id = self.product_uom_id or product.uom_id

            if self.product_uom_id != product.uom_id:
                self.price_unit = self.env['product.uom']._compute_price(product.uom_id.id, self.price_unit, self.product_uom_id.id)
            if not self.product_uom_id:
                domain = {'product_uom_id': [('category_id', '=', product.uom_id.category_id.id)]}
            return {'domain': domain}

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if self.product_uom_id:
            self._onchange_product_id()

    def _inject_quote_description(self, vals):
        if not vals.get('website_description') and vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['website_description'] = product.quote_description or product.website_description or ''
        return vals

    @api.model
    def create(self, vals):
        return super(SaleQuoteLine, self).create(self._inject_quote_description(vals))

    @api.multi
    def write(self, vals):
        return super(SaleQuoteLine, self).write(self._inject_quote_description(vals))

class SaleQuoteOption(models.Model):
    _name = "sale.quote.option"
    _description = "Quotation Option"

    template_id = fields.Many2one('sale.quote.template', string='Quotation Template Reference', ondelete='cascade', index=True, required=True)
    name = fields.Text(string='Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True)
    website_description = fields.Html(string='Option Description', translate=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits_compute=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', digits_compute=dp.get_precision('Discount'))
    uom_id = fields.Many2one('product.uom', string='Unit of Measure ', required=True)
    quantity = fields.Float(required=True, digits_compute=dp.get_precision('Product UoS'), default=1)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            domain = []
            product = self.product_id

            self.price_unit = product.list_price
            self.website_description = product.product_tmpl_id.quote_description
            self.name = product.name + (product.description_sale and '\n' + product.description_sale or '')
            self.uom_id = self.uom_id or product.uom_id

            if self.uom_id != product.uom_id:
                self.price_unit = self.env['product.uom']._compute_price(product.uom_id.id, self.price_unit, self.uom_id.id)
            if not self.uom_id:
                domain = {'uom_id': [('category_id', '=', product.uom_id.category_id.id)]}
            return {'domain': domain}

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        if self.uom_id:
            self._onchange_product_id()
