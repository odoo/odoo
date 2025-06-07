# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.http import request
from odoo.osv import expression
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_id = fields.Many2one(
        help="Website through which this order was placed for eCommerce orders.",
        comodel_name='website',
        readonly=True,
    )

    cart_recovery_email_sent = fields.Boolean(string="Cart recovery email already sent")
    shop_warning = fields.Char(string="Warning")

    # Computed fields
    website_order_line = fields.One2many(
        string="Order Lines displayed on Website",
        comodel_name='sale.order.line',
        compute='_compute_website_order_line',
    )  # should not be used for computation purpose.',
    amount_delivery = fields.Monetary(
        string="Delivery Amount",
        compute='_compute_amount_delivery',
        help="Tax included or excluded depending on the website configuration.",
    )
    cart_quantity = fields.Integer(string="Cart Quantity", compute='_compute_cart_info')
    only_services = fields.Boolean(string="Only Services", compute='_compute_cart_info')
    is_abandoned_cart = fields.Boolean(
        string="Abandoned Cart", compute='_compute_abandoned_cart', search='_search_abandoned_cart',
    )

    #=== COMPUTE METHODS ===#

    @api.depends('order_line')
    def _compute_website_order_line(self):
        for order in self:
            order.website_order_line = order.order_line.filtered(lambda sol: sol._show_in_cart())

    @api.depends('order_line.price_total', 'order_line.price_subtotal')
    def _compute_amount_delivery(self):
        self.amount_delivery = 0.0
        for order in self.filtered('website_id'):
            delivery_lines = order.order_line.filtered('is_delivery')
            if order.website_id.show_line_subtotals_tax_selection == 'tax_excluded':
                order.amount_delivery = sum(delivery_lines.mapped('price_subtotal'))
            else:
                order.amount_delivery = sum(delivery_lines.mapped('price_total'))

    @api.depends('order_line.product_uom_qty', 'order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(sol.product_id.type == 'service' for sol in order.website_order_line)

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

    def _compute_require_signature(self):
        website_orders = self.filtered('website_id')
        website_orders.require_signature = False
        super(SaleOrder, self - website_orders)._compute_require_signature()

    def _compute_payment_term_id(self):
        super()._compute_payment_term_id()
        website_orders = self.filtered(
            lambda so: so.website_id and not so.payment_term_id
        )
        if not website_orders:
            return

        # Try to find a payment term even if there wasn't any set on the partner
        default_pt = self.env.ref(
            'account.account_payment_term_immediate', raise_if_not_found=False)
        for order in website_orders:
            if default_pt and (
                order.company_id == default_pt.company_id
                or not default_pt.company_id
            ):
                order.payment_term_id = default_pt
            else:
                order.payment_term_id = order.env['account.payment.term'].search([
                    ('company_id', '=', order.company_id.id),
                ], limit=1)

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

    def _compute_user_id(self):
        """ Do not assign self.env.user as salesman for e-commerce orders.

        Leave salesman empty if no salesman is specified on partner or website.

        c/p of the logic in Website._prepare_sale_order_values
        """
        website_orders = self.filtered('website_id')
        super(SaleOrder, self - website_orders)._compute_user_id()
        for order in website_orders:
            if not order.user_id:
                order.user_id = (
                    order.website_id.salesperson_id
                    or order.partner_id.user_id.id
                    or order.partner_id.parent_id.user_id.id
                )

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('website_id'):
                website = self.env['website'].browse(vals['website_id'])
                if 'company_id' in vals:
                    company = self.env['res.company'].browse(vals['company_id'])
                    if website.company_id.id != company.id:
                        raise ValueError(_(
                            "The company of the website you are trying to sell from (%(website_company)s)"
                            " is different than the one you want to use (%(company)s)",
                            website_company=website.company_id.name,
                            company=company.name,
                        ))
                else:
                    vals['company_id'] = website.company_id.id
        return super().create(vals_list)

    #=== ACTION METHODS ===#

    def action_preview_sale_order(self):
        action = super().action_preview_sale_order()
        if action['url'].startswith('/'):
            # URL should always be relative, safety check
            action['url'] = f'/@{action["url"]}'
        return action

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
        """ Return the cart recovery template record for a set of orders.

        If they all belong to the same website, we return the website-specific template;
        otherwise we return the default template.
        If the default is not found, the empty ['mail.template'] is returned.
        """
        websites = self.mapped('website_id')
        template = websites.cart_recovery_mail_template_id if len(websites) == 1 else False
        template = template or self.env.ref('website_sale.mail_template_sale_cart_recovery', raise_if_not_found=False)
        return template or self.env['mail.template']

    #=== BUSINESS METHODS ===#

    @api.model
    def _get_note_url(self):
        website_id = self._context.get('website_id')
        if website_id:
            return self.env['website'].browse(website_id).get_base_url()
        return super()._get_note_url()

    def _get_non_delivery_lines(self):
        """Exclude delivery-related lines."""
        return self.order_line.filtered(lambda line: not line.is_delivery)

    def _get_amount_total_excluding_delivery(self):
        return sum(self._get_non_delivery_lines().mapped('price_total'))

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

    def _update_address(self, partner_id, fnames=None):
        if not fnames:
            return

        fpos_before = self.fiscal_position_id
        pricelist_before = self.pricelist_id

        self.write(dict.fromkeys(fnames, partner_id))

        fpos_changed = fpos_before != self.fiscal_position_id
        if fpos_changed:
            # Recompute taxes on fpos change
            self._recompute_taxes()

        # If the user has explicitly selected a valid pricelist, we don't want to change it
        if selected_pricelist_id := request.session.get('website_sale_selected_pl_id'):
            selected_pricelist = (
                self.env['product.pricelist'].browse(selected_pricelist_id).exists()
            )
            if (
                selected_pricelist
                and selected_pricelist._is_available_on_website(self.website_id)
                and selected_pricelist._is_available_in_country(
                    self.partner_id.country_id.code
                )
            ):
                self.pricelist_id = selected_pricelist
            else:
               request.session.pop('website_sale_selected_pl_id', None)

        if self.pricelist_id != pricelist_before or fpos_changed:
            # Pricelist may have been recomputed by the `partner_id` field update
            # we need to recompute the prices to match the new pricelist if it changed
            self._recompute_prices()

            request.session['website_sale_current_pl'] = self.pricelist_id.id
            self.website_id.invalidate_recordset(['pricelist_id'])

        if self.carrier_id and 'partner_shipping_id' in fnames and self._has_deliverable_products():
            # Update the delivery method on shipping address change.
            delivery_methods = self._get_delivery_methods()
            delivery_method = self._get_preferred_delivery_method(delivery_methods)
            self._set_delivery_method(delivery_method)

        if 'partner_id' in fnames:
            # Only add the main partner as follower of the order
            self._message_subscribe([partner_id])

    def _cart_update_pricelist(self, pricelist_id=None):
        self.ensure_one()

        if self.pricelist_id.id != pricelist_id:
            self.pricelist_id = pricelist_id
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

        order_line = self._cart_update_order_line(product_id, quantity, order_line, **kwargs)

        if (
            order_line
            # Combo product lines will be checked after creating all of their combo item lines.
            and order_line.product_template_id.type != 'combo'
            and not order_line.combo_item_id
            and order_line.price_unit == 0
            and self.website_id.prevent_zero_price_sale
            and product.service_tracking not in self.env['product.template']._get_product_types_allow_zero_price()
        ):
            raise UserError(_(
                "The given product does not have a price therefore it cannot be added to cart.",
            ))
        if self.only_services:
            self._remove_delivery_line()
        elif self.carrier_id:
            # Recompute the delivery rate.
            rate = self.carrier_id.rate_shipment(self)
            if rate['success']:
                self.order_line.filtered(lambda line: line.is_delivery).price_unit = rate['price']
            else:
                self._remove_delivery_line()

        return {
            'line_id': order_line.id,
            'quantity': quantity,
            'option_ids': list(set(order_line.linked_line_ids.filtered(
                lambda sol: sol.order_id == order_line.order_id).ids)
            ),
            'warning': warning,
        }

    def _cart_find_product_line(
        self,
        product_id,
        line_id=None,
        linked_line_id=False,
        no_variant_attribute_value_ids=None,
        **kwargs
    ):
        """Find the cart line matching the given parameters.

        Custom attributes won't be matched (but no_variant & dynamic ones will be)

        :param int product_id: the product being added/removed, as a `product.product` id
        :param int line_id: optional, the line the customer wants to edit (/shop/cart page), as a
            `sale.order.line` id
        :param int linked_line_id: optional, the parent line (for optional products), as a
            `sale.order.line` id
        :param list optional_product_ids: optional, the optional products of the line, as a list
            of `product.product` ids
        :param list no_variant_attribute_value_ids: list of `product.template.attribute.value` ids
            whose attribute is configured as `no_variant`
        :param dict kwargs: unused parameters, maybe used in overrides or other cart update methods
        """
        self.ensure_one()

        if not self.order_line:
            return self.env['sale.order.line']

        if line_id:
            # If we update a specific line, there is no need to filter anything else
            return self.order_line.filtered(
                lambda sol: sol.product_id.id == product_id and sol.id == line_id
            )

        product = self.env['product.product'].browse(product_id)
        if product.type == 'combo':
            return self.env['sale.order.line']

        domain = [
            ('product_id', '=', product_id),
            ('product_custom_attribute_value_ids', '=', False),
            ('linked_line_id', '=', linked_line_id),
            ('combo_item_id', '=', False),
        ]

        filtered_sol = self.order_line.filtered_domain(domain)
        if not filtered_sol:
            return self.env['sale.order.line']

        if product.product_tmpl_id._has_no_variant_attributes():
            filtered_sol = filtered_sol.filtered(
                lambda sol:
                    sol.product_no_variant_attribute_value_ids.ids == no_variant_attribute_value_ids
            )

        return filtered_sol

    # hook to be overridden
    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        return new_qty, ''

    def _prepare_order_line_values(
        self, product_id, quantity, linked_line_id=False,
        no_variant_attribute_value_ids=None, product_custom_attribute_values=None,
        combo_item_id=None,
        **kwargs
    ):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)

        no_variant_attribute_values = product.env['product.template.attribute.value'].browse(
            no_variant_attribute_value_ids
        )
        received_combination = product.product_template_attribute_value_ids | no_variant_attribute_values
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
            'combo_item_id': combo_item_id,
        }

        # add no_variant attributes that were not received
        no_variant_attribute_values |= combination.filtered(
            lambda ptav: ptav.attribute_id.create_variant == 'no_variant'
        )

        if no_variant_attribute_values:
            values['product_no_variant_attribute_value_ids'] = [Command.set(no_variant_attribute_values.ids)]

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
                    and product._website_show_quick_add()
                    and product.filtered_domain(self.env['product.product']._check_company_domain(line.company_id))
                    and product._is_variant_possible(parent_combination=combination)
                    and (
                        not self.website_id.prevent_zero_price_sale
                        or product._get_contextual_price()
                    )
                )

        return random.sample(all_accessory_products, len(all_accessory_products))

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
        return super()._message_post_after_hook(message, msg_vals)

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

    def _is_reorder_allowed(self):
        self.ensure_one()
        return self.state == 'sale' and any(
            line._is_reorder_allowed() for line in self.order_line if line.product_id
        )

    def _filter_can_send_abandoned_cart_mail(self):
        self.website_id.ensure_one()
        abandoned_datetime = datetime.utcnow() - relativedelta(hours=self.website_id.cart_abandoned_delay)

        sales_after_abandoned_date = self.env['sale.order'].search([
            ('state', '=', 'sale'),
            ('partner_id', 'in', self.partner_id.ids),
            ('create_date', '>=', abandoned_datetime),
            ('website_id', '=', self.website_id.id),
        ])
        latest_create_date_per_partner = {}
        for sale in self:
            if sale.partner_id not in latest_create_date_per_partner:
                latest_create_date_per_partner[sale.partner_id] = sale.create_date
            else:
                latest_create_date_per_partner[sale.partner_id] = max(latest_create_date_per_partner[sale.partner_id], sale.create_date)
        has_later_sale_order = {}
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

    def _has_deliverable_products(self):
        """ Return whether the order has lines with products that should be delivered.

        :return: Whether the order has deliverable products.
        :rtype: bool
        """
        return bool(self.order_line.product_id) and not self.only_services

    def _remove_delivery_line(self):
        super()._remove_delivery_line()
        self.pickup_location_data = {}  # Reset the pickup location data.

    def _get_preferred_delivery_method(self, available_delivery_methods):
        """ Get the preferred delivery method based on available delivery methods for the order.

        The preferred delivery method is selected as follows:

        1. The one that is already set if it is compatible.
        2. The default one if compatible.
        3. The first compatible one.

        :param delivery.carrier available_delivery_methods: The available delivery methods for
               the order.
        :return: The preferred delivery method for the order.
        :rtype: delivery.carrier
        """
        self.ensure_one()

        delivery_method = self.carrier_id
        if available_delivery_methods and delivery_method not in available_delivery_methods:
            if self.partner_shipping_id.property_delivery_carrier_id in available_delivery_methods:
                delivery_method = self.partner_shipping_id.property_delivery_carrier_id
            else:
                delivery_method = available_delivery_methods[0]
        return delivery_method

    def _set_delivery_method(self, delivery_method, rate=None):
        """ Set the delivery method on the order and create a delivery line if the shipment rate can
         be retrieved.

        :param delivery.carrier delivery_method: The delivery_method to set on the order.
        :param dict rate: The rate of the delivery method.
        :return: None
        """
        self.ensure_one()

        self._remove_delivery_line()
        if not delivery_method or not self._has_deliverable_products():
            return

        rate = rate or delivery_method.rate_shipment(self)
        if rate.get('success'):
            self.set_delivery_line(delivery_method, rate['price'])

    def _get_delivery_methods(self):
        # searching on website_published will also search for available website (_search method on computed field)
        return self.env['delivery.carrier'].sudo().search([
            ('website_published', '=', True),
        ]).filtered(lambda carrier: carrier._is_available_for_order(self))

    #=== TOOLING ===#

    def _is_anonymous_cart(self):
        """ Return whether the cart was created by the public user and no address was added yet.

        Note: `self.ensure_one()`

        :return: Whether the cart is anonymous.
        :rtype: bool
        """
        self.ensure_one()
        return self.partner_id.id == request.website.user_id.sudo().partner_id.id

    def _get_lang(self):
        res = super()._get_lang()

        if self.website_id and request and request.is_frontend:
            # Use request lang as cart lang if request comes from frontend
            return request.env.lang

        return res

    def _get_shop_warning(self, clear=True):
        self.ensure_one()
        warn = self.shop_warning
        if clear:
            self.shop_warning = ''
        return warn

    def _is_cart_ready(self):
        """ Whether the cart is valid and can be confirmed (and paid for)

        :rtype: bool
        """
        return True

    def _check_cart_is_ready_to_be_paid(self):
        """ Whether the cart is valid and the user can proceed to the payment

        :rtype: bool
        """
        if not self._is_cart_ready():
            raise ValidationError(_(
                "Your cart is not ready to be paid, please verify previous steps."
            ))

        if not self.only_services and not self.carrier_id:
            raise ValidationError(_("No shipping method is selected."))

    def _is_delivery_ready(self):
        return not self._has_deliverable_products() or self.carrier_id
