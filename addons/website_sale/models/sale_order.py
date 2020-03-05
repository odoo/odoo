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

    @api.depends('order_line')
    def _compute_website_order_line(self):
        for order in self:
            order.website_order_line = order.order_line

    @api.depends('order_line.product_uom_qty', 'order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(l.product_id.type in ('service', 'digital') for l in order.website_order_line)

    @api.depends('website_id', 'date_order', 'order_line', 'state', 'partner_id')
    def _compute_abandoned_cart(self):
        for order in self:
            # a quotation can be considered as an abandonned cart if it is linked to a website,
            # is in the 'draft' state and has an expiration date
            if order.website_id and order.state == 'draft' and order.date_order:
                public_partner_id = order.website_id.user_id.partner_id
                # by default the expiration date is 1 hour if not specified on the website configuration
                abandoned_delay = order.website_id.cart_abandoned_delay or 1.0
                abandoned_datetime = datetime.utcnow() - relativedelta(hours=abandoned_delay)
                order.is_abandoned_cart = bool(order.date_order <= abandoned_datetime and order.partner_id != public_partner_id and order.order_line)
            else:
                order.is_abandoned_cart = False

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
        return expression.distribute_not(['!'] + abandoned_domain)  # negative domain

    def _prepare_line_values(self, product, qty, **kwargs):
        # VFE TODO with_company order.company_id or managed at sale module level?
        no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
        received_no_variant_values = self.env['product.template.attribute.value'].browse([int(ptav['value']) for ptav in no_variant_attribute_values])
        received_combination = product.product_template_attribute_value_ids | received_no_variant_values
        product_template = product.product_tmpl_id

        # handle all cases where incorrect or incomplete data are received
        combination = product_template._get_closest_possible_combination(received_combination)

        # get or create (if dynamic) the correct variant
        product = product_template._create_product_variant(combination)

        if not product:
            raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))

        pnvav = combination - product.product_template_attribute_value_ids

        values = {
            'product_id': product.id,
            'product_uom_qty': qty,
            'order_id': self.id,
            'product_uom': product.uom_id.id,
        }

        # save no_variant attributes values
        if pnvav:
            values['product_no_variant_attribute_value_ids'] = [
                (6, 0, pnvav.ids)
            ]

        custom_values = kwargs.get('product_custom_attribute_values') or []

        # save is_custom attributes values
        if custom_values:
            values['product_custom_attribute_value_ids'] = [(0, 0, {
                'custom_product_template_attribute_value_id': custom_value['custom_product_template_attribute_value_id'],
                'custom_value': custom_value.get('custom_value', ''),
            }) for custom_value in custom_values]

        return values

    def _check_quantity(self, product, old_qty, new_qty, line=None):
        qty, warning = new_qty, ''
        return qty, warning

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()

        # Subsequent SO modifications have to be done in customer language.
        self = self.with_context(lang=self.sudo().partner_id.lang).with_company(self.company_id)

        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))

        SaleOrderLineSudo = self.env['sale.order.line'].sudo()
        product = self.env['product.product'].browse(int(product_id))

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
        if line_id:
            order_line = SaleOrderLineSudo.browse(line_id)
            if order_line.product_id != product:
                order_line = self.env['sale.order.line']

        # Create line if no line with product_id can be located
        if not order_line:
            if not product:
                raise UserError(_("The given product does not exist therefore it cannot be added to cart."))

            # Create the line
            quantity = set_qty or add_qty
            quantity, warning = self._check_quantity(product, 0, quantity)
            # VFE FIXME do not create if quantity <= 0
            values = self._prepare_line_values(product, quantity, **kwargs)
            order_line = SaleOrderLineSudo.create(values)

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))

            order_line.product_id_change()
        else:
            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty is not None:
                quantity = order_line.product_uom_qty + (add_qty or 0)

            quantity, warning = self._check_quantity(product, order_line.product_uom_qty, quantity, order_line)
            # Remove zero or negative lines
            if quantity <= 0:
                linked_line = order_line.linked_line_id
                order_line.unlink()
                if linked_line:
                    # update description of the parent
                    linked_product = linked_line.product_id
                    # VFE TODO cleanup get_sale_order_line_multiline_description_sale broll?
                    linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
            else:
                # update line
                order_line.product_uom_qty = quantity
                order_line.quantity_change()

                # link a product to the sales order
                if kwargs.get('linked_line_id'):
                    linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
                    order_line.write({
                        'linked_line_id': linked_line.id,
                    })
                    linked_product = linked_line.product_id
                    linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
                    # Generate the description with everything. This is done after
                    # creating because the following related fields have to be set:
                    # - product_no_variant_attribute_value_ids
                    # - product_custom_attribute_value_ids
                    # - linked_line_id
                    order_line.name = order_line.get_sale_order_line_multiline_description_sale(product)

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id) if order_line else self.env['sale.order.line']

        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids)), 'warning': warning}

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        for order in self:
            products = order.website_order_line.mapped('product_id')
            accessory_products = self.env['product.product']
            for line in order.website_order_line.filtered(lambda l: l.product_id):
                combination = line.product_id.product_template_attribute_value_ids + line.product_no_variant_attribute_value_ids
                accessory_products |= line.product_id.accessory_product_ids.filtered(lambda product:
                    product.website_published and
                    product not in products and
                    product._is_variant_possible(parent_combination=combination) and
                    (product.company_id == line.company_id or not product.company_id)
                )

            return random.sample(accessory_products, len(accessory_products))

    def action_recovery_email_send(self):
        for order in self:
            order._portal_ensure_token()
        composer_form_view_id = self.env.ref('mail.email_compose_message_wizard_form').id

        template_id = self._get_cart_recovery_template().id

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'view_id': composer_form_view_id,
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass_mail' if len(self.ids) > 1 else 'comment',
                'default_res_id': self.ids[0],
                'default_model': 'sale.order',
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'website_sale_send_recovery_email': True,
                'active_ids': self.ids,
            },
        }

    def _get_cart_recovery_template(self):
        """
        Return the cart recovery template record for a set of orders.
        If they all belong to the same website, we return the website-specific template;
        otherwise we return the default template.
        If the default is not found, the empty ['mail.template'] is returned.
        """
        websites = self.mapped('website_id')
        template = websites.cart_recovery_mail_template_id if len(websites) == 1 else False
        template = template or self.env.ref('website_sale.mail_template_sale_cart_recovery', raise_if_not_found=False)
        return template or self.env['mail.template']

    def _cart_recovery_email_send(self):
        """Send the cart recovery email on the current recordset,
        making sure that the portal token exists to avoid broken links, and marking the email as sent.
        Similar method to action_recovery_email_send, made to be called in automated actions.
        Contrary to the former, it will use the website-specific template for each order."""
        sent_orders = self.env['sale.order']
        for order in self:
            template = order._get_cart_recovery_template()
            if template:
                order._portal_ensure_token()
                template.send_mail(order.id)
                sent_orders |= order
        sent_orders.write({'cart_recovery_email_sent': True})


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    name_short = fields.Char(compute="_compute_name_short")

    linked_line_id = fields.Many2one('sale.order.line', string='Linked Order Line', domain="[('order_id', '!=', order_id)]", ondelete='cascade')
    option_line_ids = fields.One2many('sale.order.line', 'linked_line_id', string='Options Linked')

    def get_sale_order_line_multiline_description_sale(self, product):
        description = super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale(product)
        if self.linked_line_id:
            description += "\n" + _("Option for: %s") % self.linked_line_id.product_id.display_name
        if self.option_line_ids:
            description += "\n" + '\n'.join([_("Option: %s") % option_line.product_id.display_name for option_line in self.option_line_ids])
        return description

    @api.depends('product_id.display_name')
    def _compute_name_short(self):
        """ Compute a short name for this sale order line, to be used on the website where we don't have much space.
            To keep it short, instead of using the first line of the description, we take the product name without the internal reference.
        """
        for record in self:
            record.name_short = record.product_id.with_context(display_default_code=False).display_name

    def get_description_following_lines(self):
        return self.name.splitlines()[1:]
