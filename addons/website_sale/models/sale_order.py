# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.http import request
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    website_order_line = fields.One2many(
        'sale.order.line',
        compute='_compute_website_order_line',
        string='Order Lines displayed on Website',
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    cart_quantity = fields.Integer(compute='_compute_cart_info', string='Cart Quantity')
    only_services = fields.Boolean(compute='_compute_cart_info', string='Only Services')
    is_abandoned_cart = fields.Boolean('Abandoned Cart', compute='_compute_abandoned_cart', search='_search_abandoned_cart')
    cart_recovery_email_sent = fields.Boolean('Cart recovery email already sent')
    website_id = fields.Many2one('website', string='Website', readonly=True,
                                 help='Website through which this order was placed.')

    @api.one
    def _compute_website_order_line(self):
        self.website_order_line = self.order_line

    @api.multi
    @api.depends('website_order_line.product_uom_qty', 'website_order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(l.product_id.type in ('service', 'digital') for l in order.website_order_line)

    @api.multi
    @api.depends('website_id', 'date_order', 'order_line', 'state', 'partner_id')
    def _compute_abandoned_cart(self):
        abandoned_delay = self.website_id and self.website_id.cart_abandoned_delay or 1.0
        abandoned_datetime = datetime.utcnow() - relativedelta(hours=abandoned_delay)
        for order in self:
            domain = order.date_order and order.date_order <= abandoned_datetime and order.state == 'draft' and order.partner_id.id != self.env.ref('base.public_partner').id and order.order_line
            order.is_abandoned_cart = bool(domain)

    def _search_abandoned_cart(self, operator, value):
        abandoned_delay = self.website_id and self.website_id.cart_abandoned_delay or 1.0
        abandoned_datetime = fields.Datetime.to_string(datetime.utcnow() - relativedelta(hours=abandoned_delay))
        abandoned_domain = expression.normalize_domain([
            ('date_order', '<=', abandoned_datetime),
            ('website_id', '!=', False),
            ('state', '=', 'draft'),
            ('partner_id', '!=', self.env.ref('base.public_partner').id),
            ('order_line', '!=', False)
        ])
        # is_abandoned domain possibilities
        if (operator not in expression.NEGATIVE_TERM_OPERATORS and value) or (operator in expression.NEGATIVE_TERM_OPERATORS and not value):
            return abandoned_domain
        return expression.distribute_not(abandoned_domain)  # negative domain

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)

        # split lines with the same product if it has untracked attributes
        if product and product.mapped('attribute_line_ids').filtered(lambda r: not r.attribute_id.create_variant == 'always') and not line_id:
            return self.env['sale.order.line']

        domain = [('order_id', '=', self.id), ('product_id', '=', product_id)]
        if line_id:
            domain += [('id', '=', line_id)]
        else:
            domain += [('product_custom_attribute_value_ids', '=', False)]

        lines = self.env['sale.order.line'].sudo().search(domain)

        if line_id:
            return lines
        linked_line_id = kwargs.get('linked_line_id', False)
        optional_product_ids = set(kwargs.get('optional_product_ids', []))

        lines = lines.filtered(lambda line: line.linked_line_id.id == linked_line_id)
        if optional_product_ids:
            # only match the lines with the same chosen optional products on the existing lines
            lines = lines.filtered(lambda line: optional_product_ids == set(line.mapped('option_line_ids.product_id.id')))
        else:
            lines = lines.filtered(lambda line: not line.option_line_ids)

        return lines

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product_context.update({
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.env['product.product'].with_context(product_context).browse(product_id)
        pu = product.price
        if order.pricelist_id and order.partner_id:
            order_line = order._cart_find_product_line(product.id)
            if order_line:
                pu = self.env['account.tax']._fix_tax_included_price_company(pu, product.taxes_id, order_line[0].tax_id, self.company_id)

        return {
            'product_id': product_id,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': pu,
        }

    @api.multi
    def _get_line_description(self, order_id, product_id, no_variant_attribute_values=None, custom_values=None):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product = self.env['product.product'].with_context(product_context).browse(product_id)

        name = product.display_name

        if product.description_sale:
            name += '\n%s' % (product.description_sale)

        if no_variant_attribute_values:
            name += ''.join(['\n%s: %s' % (attribute_value['attribute_name'], attribute_value['attribute_value_name'])
                for attribute_value in no_variant_attribute_values])

        if custom_values:
            name += ''.join(['\n%s: %s' % (custom_value['attribute_value_name'], custom_value['custom_value']) for custom_value in custom_values])

        return name

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()

        try:
            if add_qty:
                add_qty = float(add_qty)
        except ValueError:
            add_qty = 1
        try:
            if set_qty:
                set_qty = float(set_qty)
        except ValueError:
            set_qty = 0
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))
        if line_id is not False:
            order_lines = self._cart_find_product_line(product_id, line_id, **kwargs)
            order_line = order_lines and order_lines[0]

        # Create line if no line with product_id can be located
        if not order_line:
            values = self._website_product_id_change(self.id, product_id, qty=1)

            custom_values = kwargs.get('product_custom_attribute_values')
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'attribute_value_id': custom_value['attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]

            no_variant_attribute_values = kwargs.get('no_variant_attribute_values')
            if no_variant_attribute_values:
                values['product_no_variant_attribute_value_ids'] = [
                    (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
                ]

            values['name'] = self._get_line_description(self.id, product_id, no_variant_attribute_values=no_variant_attribute_values, custom_values=custom_values)
            order_line = SaleOrderLineSudo.create(values)

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            values = self._website_product_id_change(self.id, product_id, qty=quantity)
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context = dict(self.env.context)
                product_context.setdefault('lang', order.partner_id.lang)
                product_context.update({
                    'partner': order.partner_id.id,
                    'quantity': quantity,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                })
                product = self.env['product.product'].with_context(product_context).browse(product_id)
                values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                    order_line._get_display_price(product),
                    order_line.product_id.taxes_id,
                    order_line.tax_id,
                    self.company_id
                )

            order_line.write(values)

        # link a product to the sales order
        if kwargs.get('linked_line_id'):
            linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
            order_line.write({
                'linked_line_id': linked_line.id,
                'name': order_line.name + "\n" + _("Option for:") + ' ' + linked_line.product_id.display_name,
            })
            linked_line.write({"name": linked_line.name + "\n" + _("Option:") + ' ' + order_line.product_id.display_name})

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)
        for option_line_id in option_lines:
            self._cart_update(option_line_id.product_id.id, option_line_id.id, add_qty, set_qty, **kwargs)

        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        for order in self:
            accessory_products = order.website_order_line.mapped('product_id.accessory_product_ids').filtered(lambda product: product.website_published)
            products = order.website_order_line.mapped('product_id')
            accessory_products -= products

            for product in products:
                for product_template in accessory_products.mapped('product_tmpl_id'):
                    template_accessory_products = accessory_products.filtered(lambda accessory_product: accessory_product.product_tmpl_id == product_template)
                    # remove from the accessories the ones that are not available for the selected product
                    accessory_products -= template_accessory_products - product_template.get_filtered_variants(product)

            return random.sample(accessory_products, len(accessory_products))

    @api.multi
    def action_recovery_email_send(self):
        composer_form_view_id = self.env.ref('mail.email_compose_message_wizard_form').id
        try:
            default_template = self.env.ref('website_sale.mail_template_sale_cart_recovery', raise_if_not_found=False)
            default_template_id = default_template.id if default_template else False
            template_id = self.website_id and self.website_id.cart_recovery_mail_template_id.id or default_template_id
        except:
            template_id = False
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'view_id': composer_form_view_id,
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass_mail',
                'default_res_id': self.ids[0],
                'default_model': 'sale.order',
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'website_sale_send_recovery_email': True,
                'active_ids': self.ids,
            },
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    name_short = fields.Char(compute="_compute_name_short")

    linked_line_id = fields.Many2one('sale.order.line', string='Linked Order Line', domain="[('order_id', '!=', order_id)]", ondelete='cascade')
    option_line_ids = fields.One2many('sale.order.line', 'linked_line_id', string='Options Linked')

    @api.multi
    @api.depends('product_id.display_name')
    def _compute_name_short(self):
        """ Compute a short name for this sale order line, to be used on the website where we don't have much space.
            To keep it short, instead of using the first line of the description, we take the product name without the internal reference.
        """
        for record in self:
            record.name_short = record.product_id.with_context(display_default_code=False).display_name

    def get_description_following_lines(self):
        return self.name.splitlines()[1:]