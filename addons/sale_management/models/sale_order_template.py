# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class SaleOrderTemplate(models.Model):
    _name = "sale.order.template"
    _description = "Quotation Template"

    def _get_default_require_signature(self):
        return self.env.user.company_id.portal_confirmation_sign

    def _get_default_require_payment(self):
        return self.env.user.company_id.portal_confirmation_pay

    name = fields.Char('Quotation Template', required=True)
    sale_order_template_line_ids = fields.One2many('sale.order.template.line', 'sale_order_template_id', 'Lines', copy=True)
    note = fields.Text('Terms and conditions', translate=True)
    sale_order_template_option_ids = fields.One2many('sale.order.template.option', 'sale_order_template_id', 'Optional Products', copy=True)
    number_of_days = fields.Integer('Quotation Duration',
        help='Number of days for the validity date computation of the quotation')
    require_signature = fields.Boolean('Online Signature', default=_get_default_require_signature, help='Request a online signature to the customer in order to confirm orders automatically.')
    require_payment = fields.Boolean('Online Payment', default=_get_default_require_payment, help='Request an online payment to the customer in order to confirm orders automatically.')
    mail_template_id = fields.Many2one(
        'mail.template', 'Confirmation Mail',
        domain=[('model', '=', 'sale.order')],
        help="This e-mail template will be sent on confirmation. Leave empty to send nothing.")
    active = fields.Boolean(default=True, help="If unchecked, it will allow you to hide the quotation template without removing it.")

    @api.multi
    def write(self, vals):
        if 'active' in vals and not vals.get('active'):
            template_id = self.env['ir.default'].get('sale.order', 'sale_order_template_id')
            for template in self:
                if template_id and template_id == template.id:
                    raise UserError('Before archiving "%s" please select another default template in the settings.' % template.name)
        return super(SaleOrderTemplate, self).write(vals)


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _description = "Quotation Template Line"
    _order = 'sale_order_template_id, sequence, id'

    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of sale quote lines.",
        default=10)
    sale_order_template_id = fields.Many2one('sale.order.template', 'Quotation Template Reference', required=True,
        ondelete='cascade', index=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)])
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    product_uom_qty = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        if self.product_id:
            name = self.product_id.name_get()[0][1]
            if self.product_id.description_sale:
                name += '\n' + self.product_id.description_sale
            self.name = name
            self.price_unit = self.product_id.lst_price
            self.product_uom_id = self.product_id.uom_id.id
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
            return {'domain': domain}

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        if self.product_id and self.product_uom_id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.lst_price, self.product_uom_id)

    @api.model
    def create(self, values):
        if values.get('display_type', self.default_get(['display_type'])['display_type']):
            values.update(product_id=False, price_unit=0, product_uom_qty=0, product_uom_id=False)
        return super(SaleOrderTemplateLine, self).create(values)

    @api.multi
    def write(self, values):
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError("You cannot change the type of a sale quote line. Instead you should delete the current line and create a new line of the proper type.")
        return super(SaleOrderTemplateLine, self).write(values)

    _sql_constraints = [
        ('accountable_product_id_required',
            "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL))",
            "Missing required product and UoM on accountable sale quote line."),

        ('non_accountable_fields_null',
            "CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom_id IS NULL))",
            "Forbidden product, unit price, quantity, and UoM on non-accountable sale quote line"),
    ]


class SaleOrderTemplateOption(models.Model):
    _name = "sale.order.template.option"
    _description = "Quotation Template Option"

    sale_order_template_id = fields.Many2one('sale.order.template', 'Quotation Template Reference', ondelete='cascade',
        index=True, required=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'))
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id
        self.price_unit = product.list_price
        name = product.name
        if self.product_id.description_sale:
            name += '\n' + self.product_id.description_sale
        self.name = name
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
