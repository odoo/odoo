# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    website_order_line = fields.One2many(
        'sale.order.line',
        compute='_compute_website_order_line',
        string='Order Lines displayed on Website',
    ) # should not be used for computation purpose.',
    cart_quantity = fields.Integer(compute='_compute_cart_info', string='Cart Quantity')
    only_services = fields.Boolean(compute='_compute_cart_info', string='Only Services')
    is_abandoned_cart = fields.Boolean('Abandoned Cart', compute='_compute_abandoned_cart', search='_search_abandoned_cart')
    cart_recovery_email_sent = fields.Boolean('Cart recovery email already sent')
    website_id = fields.Many2one('website', string='Website', readonly=True,
                                 help='Website through which this order was placed for eCommerce orders.')
    shop_warning = fields.Char('Warning')
    amount_delivery = fields.Monetary(
        string="Delivery Amount",
        compute='_compute_amount_delivery',
        help="Tax included or excluded depending on the website configuration.",
    )
    access_point_address = fields.Json("Delivery Point Address")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('website_id'):
                website = self.env['website'].browse(vals['website_id'])
                if 'company_id' in vals:
                    company = self.env['res.company'].browse(vals['company_id'])
                    if website.company_id.id != company.id:
                        raise ValueError(_("The company of the website you are trying to sale from (%s) is different than the one you want to use (%s)", website.company_id.name, company.name))
                else:
                    vals['company_id'] = website.company_id.id
        return super().create(vals_list)

    def _compute_user_id(self):
        """Do not assign self.env.user as salesman for e-commerce orders
        Leave salesman empty if no salesman is specified on partner or website

        c/p of the logic in Website._prepare_sale_order_values
        """
        website_orders = self.filtered('website_id')
        super(SaleOrder, self - website_orders)._compute_user_id()
        for order in website_orders:
            if not order.user_id:
                order.user_id = order.website_id.salesperson_id or order.partner_id.parent_id.user_id.id or order.partner_id.user_id.id

    @api.model
    def _get_note_url(self):
        website_id = self._context.get('website_id')
        if website_id:
            return self.env['website'].browse(website_id).get_base_url()
        return super()._get_note_url()

    @api.depends('order_line')
    def _compute_website_order_line(self):
        for order in self:
            order.website_order_line = order.order_line.filtered(lambda l: l._show_in_cart())

    @api.depends('order_line.product_uom_qty', 'order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(l.product_id.type == 'service' for l in order.website_order_line)

    @api.depends('order_line.price_total', 'order_line.price_subtotal')
    def _compute_amount_delivery(self):
        self.amount_delivery = 0.0
        for order in self.filtered('website_id'):
            delivery_lines = order.order_line.filtered('is_delivery')
            if order.website_id.show_line_subtotals_tax_selection == 'tax_excluded':
                order.amount_delivery = sum(delivery_lines.mapped('price_subtotal'))
            else:
                order.amount_delivery = sum(delivery_lines.mapped('price_total'))

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

    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        super()._compute_payment_term_id()
        for order in self:
            if order.website_id:
                order.payment_term_id = order.website_id.with_company(order.company_id).sale_get_payment_term(order.partner_id)

    def _search_abandoned_cart(self, operator, value):
        website_ids = self.env['website'].search_read(fields=['id', 'cart_abandoned_delay', 'partner_id'])
        deadlines = [[
            '&', '&',
            ('website_id', '=', website_id['id']),
            ('date_order', '<=', fields.Datetime.to_string(datetime.utcnow() - relativedelta(hours=website_id['cart_abandoned_delay'] or 1.0))),
            ('partner_id', '!=', website_id['partner_id'][0])
        ] for website_id in website_ids]
        abandoned_domain = [
            ('state', '=', 'draft'),
            ('order_line', '!=', False)
        ]
        abandoned_domain.extend(expression.OR(deadlines))
        abandoned_domain = expression.normalize_domain(abandoned_domain)
        # is_abandoned domain possibilities
        if (operator not in expression.NEGATIVE_TERM_OPERATORS and value) or (operator in expression.NEGATIVE_TERM_OPERATORS and not value):
            return abandoned_domain
        return expression.distribute_not(['!'] + abandoned_domain)  # negative domain

    def _cart_update_order_line(self, product_id, quantity, order_line, **kwargs):
        self.ensure_one()

        if order_line and quantity <= 0:
            # Remove zero or negative lines
            order_line.unlink()
            order_line = self.env['sale.order.line']
        elif order_line:
            # Update existing line
            update_values = self._prepare_order_line_update_values(order_line, quantity, **kwargs)
            if update_values:
                self._update_cart_line_values(order_line, update_values)
        elif quantity > 0:
            # Create new line
            order_line_values = self._prepare_order_line_values(product_id, quantity, **kwargs)
            order_line = self.env['sale.order.line'].sudo().create(order_line_values)
        return order_line

    def _cart_update_pricelist(self, pricelist_id=None, update_pricelist=False):
        self.ensure_one()

        previous_pricelist_id = self.pricelist_id.id

        if pricelist_id:
            self.pricelist_id = pricelist_id

        if update_pricelist:
            self._compute_pricelist_id()

        if update_pricelist or previous_pricelist_id != self.pricelist_id.id:
            self._recompute_prices()

    def _cart_update(self, product_id, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()
        self = self.with_company(self.company_id)

        if self.state != 'draft':
            request.session.pop('sale_order_id', None)
            request.session.pop('website_sale_cart_quantity', None)
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))

        product = self.env['product.product'].browse(product_id).exists()
        if add_qty and (not product or not product._is_add_to_cart_allowed()):
            raise UserError(_("The given product does not exist therefore it cannot be added to cart."))

        if line_id is not False:
            order_line = self._cart_find_product_line(product_id, line_id, **kwargs)[:1]
        else:
            order_line = self.env['sale.order.line']

        try:
            if add_qty:
                add_qty = int(add_qty)
        except ValueError:
            add_qty = 1

        try:
            if set_qty:
                set_qty = int(set_qty)
        except ValueError:
            set_qty = 0

        quantity = 0
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            if order_line:
                quantity = order_line.product_uom_qty + (add_qty or 0)
            else:
                quantity = add_qty or 0

        if quantity > 0:
            quantity, warning = self._verify_updated_quantity(
                order_line,
                product_id,
                quantity,
                **kwargs,
            )
        else:
            # If the line will be removed anyway, there is no need to verify
            # the requested quantity update.
            warning = ''

        self._remove_delivery_line()

        order_line = self._cart_update_order_line(product_id, quantity, order_line, **kwargs)

        if (
            order_line
            and order_line.price_unit == 0
            and self.website_id.prevent_zero_price_sale
            and product.detailed_type not in self.env['product.template']._get_product_types_allow_zero_price()
        ):
            raise UserError(_(
                "The given product does not have a price therefore it cannot be added to cart.",
            ))

        return {
            'line_id': order_line.id,
            'quantity': quantity,
            'option_ids': list(set(order_line.option_line_ids.filtered(lambda l: l.order_id == order_line.order_id).ids)),
            'warning': warning,
        }

    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        """Find the cart line matching the given parameters.

        If a product_id is given, the line will match the product only if the
        line also has the same special attributes: `no_variant` attributes and
        `is_custom` values.
        """
        self.ensure_one()
        SaleOrderLine = self.env['sale.order.line']

        if not self.order_line:
            return SaleOrderLine

        product = self.env['product.product'].browse(product_id)
        if not line_id and (
            product.product_tmpl_id.has_dynamic_attributes()
            or product.product_tmpl_id._has_no_variant_attributes()
        ):
            return SaleOrderLine

        domain = [('order_id', '=', self.id), ('product_id', '=', product_id)]
        if line_id:
            domain += [('id', '=', line_id)]
        else:
            domain += [('product_custom_attribute_value_ids', '=', False)]

        return SaleOrderLine.search(domain)

    # hook to be overridden
    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        return new_qty, ''

    def _prepare_order_line_values(
        self, product_id, quantity, linked_line_id=False,
        no_variant_attribute_values=None, product_custom_attribute_values=None,
        **kwargs
    ):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)

        no_variant_attribute_values = no_variant_attribute_values or []
        received_no_variant_values = product.env['product.template.attribute.value'].browse([
            int(ptav['value'])
            for ptav in no_variant_attribute_values
        ])
        received_combination = product.product_template_attribute_value_ids | received_no_variant_values
        product_template = product.product_tmpl_id

        # handle all cases where incorrect or incomplete data are received
        combination = product_template._get_closest_possible_combination(received_combination)

        # get or create (if dynamic) the correct variant
        product = product_template._create_product_variant(combination)

        if not product:
            raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))

        values = {
            'product_id': product.id,
            'product_uom_qty': quantity,
            'order_id': self.id,
            'linked_line_id': linked_line_id,
        }

        # add no_variant attributes that were not received
        for ptav in combination.filtered(
            lambda ptav: ptav.attribute_id.create_variant == 'no_variant' and ptav not in received_no_variant_values
        ):
            no_variant_attribute_values.append({
                'value': ptav.id,
            })

        if no_variant_attribute_values:
            values['product_no_variant_attribute_value_ids'] = [
                fields.Command.set([int(attribute['value']) for attribute in no_variant_attribute_values])
            ]

        # add is_custom attribute values that were not received
        custom_values = product_custom_attribute_values or []
        received_custom_values = product.env['product.template.attribute.value'].browse([
            int(ptav['custom_product_template_attribute_value_id'])
            for ptav in custom_values
        ])

        for ptav in combination.filtered(lambda ptav: ptav.is_custom and ptav not in received_custom_values):
            custom_values.append({
                'custom_product_template_attribute_value_id': ptav.id,
                'custom_value': '',
            })

        if custom_values:
            values['product_custom_attribute_value_ids'] = [
                fields.Command.create({
                    'custom_product_template_attribute_value_id': custom_value['custom_product_template_attribute_value_id'],
                    'custom_value': custom_value['custom_value'],
                }) for custom_value in custom_values
            ]

        return values

    def _prepare_order_line_update_values(
        self, order_line, quantity, linked_line_id=False, **kwargs
    ):
        self.ensure_one()
        values = {}

        if quantity != order_line.product_uom_qty:
            values['product_uom_qty'] = quantity
        if linked_line_id and linked_line_id != order_line.linked_line_id.id:
            values['linked_line_id'] = linked_line_id

        return values

    # hook to be overridden
    def _update_cart_line_values(self, order_line, update_values):
        self.ensure_one()
        order_line.write(update_values)

    def _is_cart_ready(self):
        """Whether the cart is valid and can be confirmed (and paid for)

        :rtype: bool
        """
        return True

    def _check_cart_is_ready_to_be_paid(self):
        """"Whether the cart is valid and the user can proceed to the payment

        :rtype: bool
        """
        if not self._is_cart_ready():
            raise ValidationError(_(
                "Your cart is not ready to be paid, please verify previous steps."
            ))

        if not self.only_services and not self.carrier_id:
            raise ValidationError(_("No shipping method is selected."))

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        product_ids = set(self.website_order_line.product_id.ids)
        all_accessory_products = self.env['product.product']
        for line in self.website_order_line.filtered('product_id'):
            accessory_products = line.product_id.product_tmpl_id._get_website_accessory_product()
            if accessory_products:
                # Do not read ptavs if there is no accessory products to filter
                combination = line.product_id.product_template_attribute_value_ids + line.product_no_variant_attribute_value_ids
                all_accessory_products |= accessory_products.filtered(lambda product:
                    product.id not in product_ids
                    and product.filtered_domain(self.env['product.product']._check_company_domain(line.company_id))
                    and product._is_variant_possible(parent_combination=combination)
                    and (
                        not self.website_id.prevent_zero_price_sale
                        or product._get_contextual_price()
                    )
                )

        return random.sample(all_accessory_products, len(all_accessory_products))

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
                'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                'default_res_ids': self.ids,
                'default_model': 'sale.order',
                'default_template_id': template_id,
                'website_sale_send_recovery_email': True,
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
        Similar method to action_recovery_email_send, made to be called in automation rules.
        Contrary to the former, it will use the website-specific template for each order."""
        sent_orders = self.env['sale.order']
        for order in self:
            template = order._get_cart_recovery_template()
            if template:
                order._portal_ensure_token()
                template.send_mail(order.id)
                sent_orders |= order
        sent_orders.write({'cart_recovery_email_sent': True})

    def _message_mail_after_hook(self, mails):
        """ After sending recovery cart emails, update orders to avoid sending
        it again. """
        if self.env.context.get('website_sale_send_recovery_email'):
            self.filtered_domain([
                ('cart_recovery_email_sent', '=', False),
                ('is_abandoned_cart', '=', True)
            ]).cart_recovery_email_sent = True
        return super()._message_mail_after_hook(mails)

    def _message_post_after_hook(self, message, msg_vals):
        """ After sending recovery cart emails, update orders to avoid sending
        it again. """
        if self.env.context.get('website_sale_send_recovery_email'):
            self.cart_recovery_email_sent = True
        return super(SaleOrder, self)._message_post_after_hook(message, msg_vals)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ In case of cart recovery email, update link to redirect directly
        to the cart (like ``mail_template_sale_cart_recovery`` template). """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        customer_portal_group = next((group for group in groups if group[0] == 'portal_customer'), None)
        if customer_portal_group:
            access_opt = customer_portal_group[2].setdefault('button_access', {})
            if self._context.get('website_sale_send_recovery_email'):
                access_opt['title'] = _('Resume Order')
                access_opt['url'] = '%s/shop/cart?access_token=%s' % (self.get_base_url(), self.access_token)
        return groups

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if not order.transaction_ids and not order.amount_total and self._context.get('send_email'):
                order._send_order_confirmation_mail()
        return res

    def _action_confirm(self):
        for order in self:
            order_location = order.access_point_address

            if not order_location:
                continue

            # retrieve all the data :
            # name, street, city, state, zip, country
            name = order.partner_shipping_id.name
            street = order_location['pick_up_point_address']
            city = order_location['pick_up_point_town']
            zip_code = order_location['pick_up_point_postal_code']
            country = order.env['res.country'].search([('code', '=', order_location['pick_up_point_country'])]).id
            state = order.env['res.country.state'].search(['&', ('code', '=', order_location['pick_up_point_state']), ('country_id', '=', country)]).id if (order_location['pick_up_point_state'] and country) else None
            parent_id = order.partner_shipping_id.id
            email = order.partner_shipping_id.email
            phone = order.partner_shipping_id.phone

            # we can check if the current partner has a partner of type "delivery" that has the same address
            existing_partner = order.env['res.partner'].search(['&', '&', '&', '&', '&',
                                                                ('street', '=', street),
                                                                ('city', '=', city),
                                                                ('state_id', '=', state),
                                                                ('country_id', '=', country),
                                                                ('parent_id', '=', parent_id),
                                                                ('type', '=', 'delivery')], limit=1)

            if existing_partner:
                order.partner_shipping_id = existing_partner
            else:
                # if not, we create that res.partner
                order.partner_shipping_id = order.env['res.partner'].create({
                    'parent_id': parent_id,
                    'type': 'delivery',
                    'name': name,
                    'street': street,
                    'city': city,
                    'state_id': state,
                    'zip': zip_code,
                    'country_id': country,
                    'email': email,
                    'phone': phone
                })
        return super()._action_confirm()

    def _get_shop_warning(self, clear=True):
        self.ensure_one()
        warn = self.shop_warning
        if clear:
            self.shop_warning = ''
        return warn

    def _is_reorder_allowed(self):
        self.ensure_one()
        return self.state == 'sale' and any(line._is_reorder_allowed() for line in self.order_line if not line.display_type)

    def _filter_can_send_abandoned_cart_mail(self):
        self.website_id.ensure_one()
        abandoned_datetime = datetime.utcnow() - relativedelta(hours=self.website_id.cart_abandoned_delay)

        sales_after_abandoned_date = self.env['sale.order'].search([
            ('state', '=', 'sale'),
            ('partner_id', 'in', self.partner_id.ids),
            ('create_date', '>=', abandoned_datetime),
            ('website_id', '=', self.website_id.id),
        ])
        latest_create_date_per_partner = dict()
        for sale in self:
            if sale.partner_id not in latest_create_date_per_partner:
                latest_create_date_per_partner[sale.partner_id] = sale.create_date
            else:
                latest_create_date_per_partner[sale.partner_id] = max(latest_create_date_per_partner[sale.partner_id], sale.create_date)
        has_later_sale_order = dict()
        for sale in sales_after_abandoned_date:
            if has_later_sale_order.get(sale.partner_id, False):
                continue
            has_later_sale_order[sale.partner_id] = latest_create_date_per_partner[sale.partner_id] <= sale.date_order

        # Customer needs to be signed in otherwise the mail address is not known.
        # We therefore consider only sales with a known mail address.

        # If a payment processing error occurred when the customer tried to complete their checkout,
        # then the email won't be sent.

        # If all the products in the checkout are free, and the customer does not visit the shipping page to add a
        # shipping fee or the shipping fee is also free, then the email won't be sent.

        # If a potential customer creates one or more abandoned sale order and then completes a sale order before
        # the recovery email gets sent, then the email won't be sent.

        return self.filtered(
            lambda abandoned_sale_order:
            abandoned_sale_order.partner_id.email
            and not any(transaction.sudo().state == 'error' for transaction in abandoned_sale_order.transaction_ids)
            and any(not float_is_zero(line.price_unit, precision_rounding=line.currency_id.rounding) for line in abandoned_sale_order.order_line)
            and not has_later_sale_order.get(abandoned_sale_order.partner_id, False)
        )

    def action_preview_sale_order(self):
        action = super().action_preview_sale_order()
        if action['url'].startswith('/'):
            # URL should always be relative, safety check
            action['url'] = f'/@{action["url"]}'
        return action

    def _check_carrier_quotation(self, force_carrier_id=None, keep_carrier=False):
        self.ensure_one()
        DeliveryCarrier = self.env['delivery.carrier']

        if self.only_services:
            self._remove_delivery_line()
            return True
        else:
            self = self.with_company(self.company_id)
            # attempt to use partner's preferred carrier
            if not force_carrier_id and self.partner_shipping_id.property_delivery_carrier_id and not keep_carrier:
                force_carrier_id = self.partner_shipping_id.property_delivery_carrier_id.id

            carrier = force_carrier_id and DeliveryCarrier.browse(force_carrier_id) or self.carrier_id
            available_carriers = self._get_delivery_methods()
            if carrier:
                if carrier not in available_carriers:
                    carrier = DeliveryCarrier
                else:
                    # set the forced carrier at the beginning of the list to be verfied first below
                    available_carriers -= carrier
                    available_carriers = carrier + available_carriers
            if force_carrier_id or not carrier or carrier not in available_carriers:
                for delivery in available_carriers:
                    verified_carrier = delivery._match_address(self.partner_shipping_id)
                    if verified_carrier:
                        carrier = delivery
                        break
                self.write({'carrier_id': carrier.id})
            self._remove_delivery_line()
            if carrier:
                res = carrier.rate_shipment(self)
                if res.get('success'):
                    self.set_delivery_line(carrier, res['price'])
                    self.delivery_rating_success = True
                    self.delivery_message = res['warning_message']
                else:
                    self.set_delivery_line(carrier, 0.0)
                    self.delivery_rating_success = False
                    self.delivery_message = res['error_message']

        return bool(carrier)

    def _get_delivery_methods(self):
        # searching on website_published will also search for available website (_search method on computed field)
        return self.env['delivery.carrier'].sudo().search([
            ('website_published', '=', True),
        ]).filtered(lambda carrier: carrier._is_available_for_order(self))

    #=== TOOLING ===#

    def _is_public_order(self):
        self.ensure_one()
        return self.partner_id.id == request.website.user_id.sudo().partner_id.id

    def _get_lang(self):
        res = super()._get_lang()

        if self.website_id and request and request.is_frontend:
            # Use request lang as cart lang if request comes from frontend
            return request.env.lang

        return res
