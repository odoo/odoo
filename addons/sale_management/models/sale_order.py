# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Quotation Template',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    sale_order_option_ids = fields.One2many(
        'sale.order.option', 'order_id', 'Optional Products Lines',
        copy=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if self.sale_order_template_id and self.sale_order_template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.to_string(datetime.now() + timedelta(self.sale_order_template_id.number_of_days))
        return super(SaleOrder, self).copy(default=default)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        self.note = self.sale_order_template_id.note or self.note

    def _compute_line_data_for_template_change(self, line):
        return {
            'display_type': line.display_type,
            'name': line.name,
            'state': 'draft',
        }

    def _compute_option_data_for_template_change(self, option):
        if self.pricelist_id:
            price = self.pricelist_id.with_context(uom=option.uom_id.id).get_product_price(option.product_id, 1, False)
        else:
            price = option.price_unit
        return {
            'product_id': option.product_id.id,
            'name': option.name,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
            'price_unit': price,
            'discount': option.discount,
        }

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        if not self.sale_order_template_id:
            self.require_signature = self._get_default_require_signature()
            self.require_payment = self._get_default_require_payment()
            return
        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)

        order_lines = [(5, 0, 0)]
        for line in template.sale_order_template_line_ids:
            data = self._compute_line_data_for_template_change(line)
            if line.product_id:
                discount = 0
                if self.pricelist_id:
                    price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(line.product_id, 1, False)
                    if self.pricelist_id.discount_policy == 'without_discount' and line.price_unit:
                        discount = (line.price_unit - price) / line.price_unit * 100
                        price = line.price_unit

                else:
                    price = line.price_unit

                data.update({
                    'price_unit': price,
                    'discount': 100 - ((100 - discount) * (100 - line.discount) / 100),
                    'product_uom_qty': line.product_uom_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
                })
                if self.pricelist_id:
                    data.update(self.env['sale.order.line']._get_purchase_price(self.pricelist_id, line.product_id, line.product_uom_id, fields.Date.context_today(self)))
            order_lines.append((0, 0, data))

        self.order_line = order_lines
        self.order_line._compute_tax_id()

        option_lines = []
        for option in template.sale_order_template_option_ids:
            data = self._compute_option_data_for_template_change(option)
            option_lines.append((0, 0, data))
        self.sale_order_option_ids = option_lines

        if template.number_of_days > 0:
            self.validity_date = fields.Date.to_string(datetime.now() + timedelta(template.number_of_days))

        self.require_signature = template.require_signature
        self.require_payment = template.require_payment

        if template.note:
            self.note = template.note

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.sale_order_template_id and order.sale_order_template_id.mail_template_id:
                self.sale_order_template_id.mail_template_id.send_mail(order.id)
        return res

    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        user = access_uid and self.env['res.users'].sudo().browse(access_uid) or self.env.user

        if not self.sale_order_template_id or (not user.share and not self.env.context.get('force_website')):
            return super(SaleOrder, self).get_access_action(access_uid)
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'self',
            'res_id': self.id,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    sale_order_option_ids = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')

    # Take the description on the order template if the product is present in it
    @api.onchange('product_id')
    def product_id_change(self):
        domain = super(SaleOrderLine, self).product_id_change()
        if self.product_id and self.order_id.sale_order_template_id:
            for line in self.order_id.sale_order_template_id.sale_order_template_line_ids:
                if line.product_id == self.product_id:
                    self.name = line.name
                    break
        return domain


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('sale.order.line', on_delete="set null")
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('sale_ok', '=', True)])
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'))
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of optional products.")

    @api.onchange('product_id', 'uom_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
        self.price_unit = product.list_price
        self.name = product.get_product_multiline_description_sale()
        self.uom_id = self.uom_id or product.uom_id
        pricelist = self.order_id.pricelist_id
        if pricelist and product:
            partner_id = self.order_id.partner_id.id
            self.price_unit = pricelist.with_context(uom=self.uom_id.id).get_product_price(product, self.quantity, partner_id)
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.multi
    def button_add_to_order(self):
        self.add_option_to_order()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.multi
    def add_option_to_order(self):
        self.ensure_one()

        sale_order = self.order_id

        if sale_order.state not in ['draft', 'sent']:
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['sale.order.line'].create(values)
        order_line._compute_tax_id()

        self.write({'line_id': order_line.id})

    @api.multi
    def _get_values_to_add_to_order(self):
        self.ensure_one()
        return {
            'order_id': self.order_id.id,
            'price_unit': self.price_unit,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'discount': self.discount,
        }
