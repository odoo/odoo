# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import html_translate
import odoo.addons.decimal_precision as dp


class SaleQuoteTemplate(models.Model):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"

    name = fields.Char('Quotation Template', required=True)
    website_description = fields.Html('Description', translate=html_translate, sanitize_attributes=False)
    quote_line = fields.One2many('sale.quote.line', 'quote_id', 'Quotation Template Lines', copy=True)
    note = fields.Text('Terms and conditions')
    options = fields.One2many('sale.quote.option', 'template_id', 'Optional Products Lines', copy=True)
    number_of_days = fields.Integer('Quotation Duration',
        help='Number of days for the validity date computation of the quotation')
    require_payment = fields.Selection([
        (0, 'Not mandatory on website quote validation'),
        (1, 'Immediate after website order validation'),
        (2, 'Immediate after website order validation and save a token'),
    ], 'Payment', help="Require immediate payment by the customer when validating the order from the website quote")
    mail_template_id = fields.Many2one('mail.template', 'Confirmation Mail',
        help="This e-mail template will be sent on confirmation. Leave empty to send nothing.")

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

    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of sale quote lines.",
        default=10)
    quote_id = fields.Many2one('sale.quote.template', 'Quotation Template Reference', required=True,
        ondelete='cascade', index=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True)
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    website_description = fields.Html('Line Description', related='product_id.product_tmpl_id.quote_description',
        translate=html_translate)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    product_uom_qty = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        if self.product_id:
            name = self.product_id.name
            if self.product_id.description_sale:
                name += '\n' + self.product_id.description_sale
            self.name = name
            self.price_unit = self.product_id.lst_price
            self.product_uom_id = self.product_id.uom_id.id
            self.website_description = self.product_id.quote_description or self.product_id.website_description or ''
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
            return {'domain': domain}

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        if self.product_id and self.product_uom_id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.lst_price, self.product_uom_id)

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(SaleQuoteLine, self).create(values)

    @api.multi
    def write(self, values):
        values = self._inject_quote_description(values)
        return super(SaleQuoteLine, self).write(values)

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quote_description or product.website_description or ''
        return values


class SaleQuoteOption(models.Model):
    _name = "sale.quote.option"
    _description = "Quotation Option"

    template_id = fields.Many2one('sale.quote.template', 'Quotation Template Reference', ondelete='cascade',
        index=True, required=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True)
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    website_description = fields.Html('Option Description', translate=html_translate, sanitize_attributes=False)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'))
    uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id
        self.price_unit = product.list_price
        self.website_description = product.product_tmpl_id.quote_description
        self.name = product.name
        self.uom_id = product.uom_id
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.onchange('uom_id')
    def _onchange_product_uom(self):
        if not self.product_id:
            return
        if not self.uom_id:
            self.price_unit = 0.0
            return
        if self.uom_id.id != self.product_id.uom_id.id:
            self.price_unit = self.product_id.uom_id._compute_price(self.price_unit, self.uom_id)
