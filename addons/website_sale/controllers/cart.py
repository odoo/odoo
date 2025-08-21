# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import fields
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.tools import consteq
from odoo.tools.image import image_data_uri
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale


class Cart(PaymentPortal):

    @route(route='/shop/cart', type='http', auth='public', website=True, sitemap=False)
    def cart(self, id=None, access_token=None, revive_method='', **post):
        """ Display the cart page.

        This route is responsible for the main cart management and abandoned cart revival logic.

        :param str id: The abandoned cart's id.
        :param str access_token: The abandoned cart's access token.
        :param str revive_method: The revival method for abandoned carts. Can be 'merge' or 'squash'.
        :return: The rendered cart page.
        :rtype: str
        """
        if not request.website.has_ecommerce_access():
            return request.redirect('/web/login')

        order_sudo = request.cart

        values = {}
        if id and access_token:
            abandoned_order = request.env['sale.order'].sudo().browse(int(id)).exists()
            if not abandoned_order or not consteq(abandoned_order.access_token, access_token):  # wrong token (or SO has been deleted)
                raise NotFound()
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive_method == 'squash' or (revive_method == 'merge' and not request.session.get('sale_order_id')):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive_method == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session.get('sale_order_id'):  # abandoned cart found, user have to choose what to do
                values.update({'id': abandoned_order.id, 'access_token': abandoned_order.access_token})

        values.update({
            'website_sale_order': order_sudo,
            'date': fields.Date.today(),
            'suggested_products': [],
        })
        if order_sudo:
            order_sudo.order_line.filtered(lambda sol: sol.product_id and not sol.product_id.active).unlink()
            values['suggested_products'] = order_sudo._cart_accessories()
            values.update(self._get_express_shop_payment_values(order_sudo))

        values.update(request.website._get_checkout_step_values())
        values.update(self._cart_values(**post))
        values.update(self._prepare_order_history())
        return request.render('website_sale.cart', values)

    def _cart_values(self, **post):
        """
        This method is a hook to pass additional values when rendering the 'website_sale.cart' template (e.g. add
        a flag to trigger a style variation)
        """
        return {}

    @route(
        route='/shop/cart/add',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        sitemap=False
    )
    def add_to_cart(
        self,
        product_template_id,
        product_id,
        quantity=1.0,
        uom_id=None,
        product_custom_attribute_values=None,
        no_variant_attribute_value_ids=None,
        linked_products=None,
        **kwargs
    ):
        """ Adds a product to the shopping cart.

        :param int product_template_id: The product to add to cart, as a
            `product.template` id.
        :param int product_id: The product to add to cart, as a
            `product.product` id.
        :param int quantity: The quantity to add to the cart.
        :param list[dict] product_custom_attribute_values: A list of objects representing custom
            attribute values for the product. Each object contains:
            - `custom_product_template_attribute_value_id`: The custom attribute's id;
            - `custom_value`: The custom attribute's value.
        :param dict no_variant_attribute_value_ids: The selected non-stored attribute(s), as a list
            of `product.template.attribute.value` ids.
        :param list linked_products: A list of objects representing additional products linked to
            the product added to the cart. Can be combo item or optional products.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The values
        :rtype: dict
        """
        order_sudo = request.cart or request.website._create_cart()
        quantity = int(quantity)  # Do not allow float values in ecommerce by default

        product = request.env['product.product'].browse(product_id).exists()
        if not product or not product._is_add_to_cart_allowed():
            raise UserError(_(
                "The given product does not exist therefore it cannot be added to cart."
            ))

        combo_item_products = [
            product for product in linked_products or [] if product.get('combo_item_id')
        ]
        if (
            product.type == 'combo'
            and combo_item_products
        ):
            # A combo product and its items should have the same quantity (by design). If the
            # requested quantity isn't available for one or more combo items, we should lower
            # the quantity of the combo product and its items to the maximum available quantity
            # of the combo item with the least available quantity.
            combo_quantity, _warning = order_sudo._verify_updated_quantity(
                request.env['sale.order.line'],
                product_id,
                quantity,
                uom_id=product.uom_id.id,
                **kwargs
            )
            for item_product in combo_item_products:
                product = request.env['product.product'].browse(product_id)
                combo_item_quantity, _warning = order_sudo._verify_updated_quantity(
                    request.env['sale.order.line'],
                    item_product['product_id'],
                    quantity,
                    uom_id=product.uom_id.id,
                    **kwargs
                )
                combo_quantity = min(combo_quantity, combo_item_quantity)
            quantity = combo_quantity

        added_qty_per_line = {}
        values = order_sudo._cart_add(
            product_id=product_id,
            quantity=quantity,
            uom_id=uom_id,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs
        )
        line_ids = {product_template_id: values['line_id']}
        added_qty_per_line[values['line_id']] = values['added_qty']

        if linked_products and values['line_id']:
            for product_data in linked_products:
                product_sudo = request.env['product.product'].sudo().browse(
                    product_data['product_id']
                ).exists()
                if product_data['quantity'] and (
                    not product_sudo
                    or (
                        not product_sudo._is_add_to_cart_allowed()
                        # For combos, the validity of the given product will be checked
                        # through the SOline constraints (_check_combo_item_id)
                        and not product_data.get('combo_item_id')
                    )
                ):
                    raise UserError(_(
                        "The given product does not exist therefore it cannot be added to cart."
                    ))

                if product.type == 'combo' and product_data.get('combo_item_id'):
                    product_data['quantity'] = quantity
                product_values = order_sudo._cart_add(
                    product_id=product_data['product_id'],
                    quantity=product_data['quantity'],
                    uom_id=product_data.get('uom_id'),
                    product_custom_attribute_values=product_data['product_custom_attribute_values'],
                    no_variant_attribute_value_ids=[
                        int(value_id) for value_id in product_data['no_variant_attribute_value_ids']
                    ],
                    # Using `line_ids[...]` instead of `line_ids.get(...)` ensures that this throws
                    # if an optional product contains bad data.
                    linked_line_id=line_ids[product_data['parent_product_template_id']],
                    **self._get_additional_cart_update_values(product_data),
                    **kwargs,
                )
                line_ids[product_data['product_template_id']] = product_values['line_id']
                added_qty_per_line[product_values['line_id']] = product_values['added_qty']

        # The validity of a combo product line can only be checked after creating all of its combo
        # item lines.
        main_product_line = request.env['sale.order.line'].browse(values['line_id'])
        if main_product_line.product_type == 'combo':
            main_product_line._check_validity()

        return {
            'cart_quantity': order_sudo.cart_quantity,
            'notification_info': {
                **self._get_cart_notification_information(
                    order_sudo, added_qty_per_line
                ),
                'warning': values.pop('warning', ''),
            },
            'quantity': values.pop('quantity', 0),
            'tracking_info': self._get_tracking_information(order_sudo, line_ids.values()),
        }

    @route(
        route='/shop/cart/quick_add', type='jsonrpc', auth='user', methods=['POST'], website=True
    )
    def quick_add(self, product_template_id, product_id, quantity=1.0, **kwargs):
        values = self.add_to_cart(product_template_id, product_id, quantity=quantity, **kwargs)

        IrUiView = request.env['ir.ui.view']
        order_sudo = request.cart
        values['website_sale.cart_lines'] = IrUiView._render_template(
            'website_sale.cart_lines', {
                'website_sale_order': order_sudo,
                'date': fields.Date.today(),
                'suggested_products': order_sudo._cart_accessories(),
            }
        )
        values['website_sale.shorter_cart_summary'] = IrUiView._render_template(
            'website_sale.shorter_cart_summary', {
                'website_sale_order': order_sudo,
                'show_shorter_cart_summary': True,
                **self._get_express_shop_payment_values(order_sudo),
                **request.website._get_checkout_step_values(),
            }
        )
        values['website_sale.quick_reorder_history'] = IrUiView._render_template(
            'website_sale.quick_reorder_history', {
                'website_sale_order': order_sudo,
                **self._prepare_order_history(),
            }
        )
        values['cart_ready'] = order_sudo._is_cart_ready()
        return values

    def _get_express_shop_payment_values(self, order, **kwargs):
        payment_form_values = CustomerPortal._get_payment_values(
            self, order, website_id=request.website.id, is_express_checkout=True
        )
        payment_form_values.update({
            'payment_access_token': payment_form_values.pop('access_token'),  # Rename the key.
            # Do not include delivery related lines
            'minor_amount': payment_utils.to_minor_currency_units(
                order._get_amount_total_excluding_delivery(), order.currency_id
            ),
            'merchant_name': request.website.name,
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'express_checkout_route': WebsiteSale._express_checkout_route,
            'landing_route': '/shop/payment/validate',
            'payment_method_unknown_id': request.env.ref('payment.payment_method_unknown').id,
            'shipping_info_required': order._has_deliverable_products(),
            # Todo: remove in master
            'delivery_amount': payment_utils.to_minor_currency_units(
                order.amount_total - order._compute_amount_total_without_delivery(),
                order.currency_id,
            ),
            'shipping_address_update_route': WebsiteSale._express_checkout_delivery_route,
        })
        if request.website.is_public_user():
            payment_form_values['partner_id'] = -1
        return payment_form_values

    @route(
        route='/shop/cart/update',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        sitemap=False
    )
    def update_cart(self, line_id, quantity, product_id=None, **kwargs):
        """Update the quantity of a specific line of the current cart.

        :param int line_id: line to update, as a `sale.order.line` id.
        :param float quantity: new line quantity.
            0 or negative numbers will only delete the line, the ecommerce
            doesn't work with negative numbers.
        :param int|None product_id: product_id of the edited line, only used when line_id
            is falsy
        :params dict kwargs: additional parameters given to _cart_update_line_quantity calls.
        """
        order_sudo = request.cart
        quantity = int(quantity)  # Do not allow float values in ecommerce by default
        IrUiView = request.env['ir.ui.view']

        # This method must be only called from the cart page BUT in some advanced logic
        # eg. website_sale_loyalty, a cart line could be a temporary record without id.
        # In this case, the line_id must be found out through the given product id.
        if not line_id:
            line_id = order_sudo.order_line.filtered(
                lambda sol: sol.product_id.id == product_id
            )[:1].id

        values = order_sudo._cart_update_line_quantity(line_id, quantity, **kwargs)

        values['cart_quantity'] = order_sudo.cart_quantity
        values['cart_ready'] = order_sudo._is_cart_ready()
        values['amount'] = order_sudo.amount_total
        values['minor_amount'] = (
            order_sudo and payment_utils.to_minor_currency_units(
                order_sudo.amount_total, order_sudo.currency_id
            )
        ) or 0.0
        values['website_sale.cart_lines'] = IrUiView._render_template(
            'website_sale.cart_lines', {
                'website_sale_order': order_sudo,
                'date': fields.Date.today(),
                'suggested_products': order_sudo._cart_accessories()
            }
        )
        values['website_sale.total'] = IrUiView._render_template(
            'website_sale.total', {
                'website_sale_order': order_sudo,
            }
        )
        values['website_sale.quick_reorder_history'] = IrUiView._render_template(
            'website_sale.quick_reorder_history', {
                'website_sale_order': order_sudo,
                **self._prepare_order_history(),
            }
        )
        return values

    def _prepare_order_history(self):
        """Prepare the order history of the current user.

        The valid order lines of the last 10 confirmed orders are considered and grouped by date. An
        order line is not valid if:

        - Its product is already in the cart.
        - It's a combo parent line.
        - It has an unsellable product.
        - It has a zero-priced product (if the website blocks them).
        - It has an already seen product (duplicate or identical combo).

        The dates are represented by labels like "Today", "Yesterday", or "X days ago".

        :return: The order history, in the format
                 {'order_history': [{'label': str, 'lines': SaleOrderLine}, ...]}.
        :rtype: dict
        """
        def is_same_combo(line1_, line2_):
            """Check if two combo lines have the same linked product combination."""
            return line1_.linked_line_ids.product_id.ids == line2_.linked_line_ids.product_id.ids

        # Get the last 10 confirmed orders from the current website user.
        previous_orders_lines_sudo = request.env['sale.order'].sudo().search(
            [
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', '=', 'sale'),
                ('website_id', '=', request.website.id),
            ],
            order='date_order desc',
            limit=10,
        ).order_line

        # Prepare the order history.
        SaleOrderLineSudo = request.env['sale.order.line'].sudo()
        cart_lines_sudo = request.cart.order_line if request.cart else SaleOrderLineSudo
        seen_lines_sudo = SaleOrderLineSudo
        lines_per_order_date = {}
        for line_sudo in previous_orders_lines_sudo:
            # Ignore lines that are combo parents, unsellable, or zero-priced.
            product_id = line_sudo.product_id.id
            if (
                line_sudo.linked_line_id.product_type == 'combo'
                or not line_sudo._is_sellable()
                or (
                    request.website.prevent_zero_price_sale
                    and line_sudo.product_id._get_combination_info_variant()['price'] == 0
                )
            ):
                continue

            # Ignore lines that are already in the cart or have already been seen.
            is_combo = line_sudo.product_type == 'combo'
            if any(
                l.product_id.id == product_id and (not is_combo or is_same_combo(line_sudo, l))
                for l in cart_lines_sudo + seen_lines_sudo
            ):
                continue
            seen_lines_sudo |= line_sudo

            # Group lines by date.
            days_ago = (fields.Date.today() - line_sudo.order_id.date_order.date()).days
            if days_ago == 0:
                line_group_label = self.env._("Today")
            elif days_ago == 1:
                line_group_label = self.env._("Yesterday")
            else:
                line_group_label = self.env._("%s days ago", days_ago)
            lines_per_order_date.setdefault(line_group_label, SaleOrderLineSudo)
            lines_per_order_date[line_group_label] |= line_sudo

        # Flatten the line groups to get the final order history.
        return {
            'order_history': [
                {'label': label, 'lines': lines} for label, lines in lines_per_order_date.items()
            ]
        }

    @route(
        route='/shop/cart/quantity',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True
    )
    def cart_quantity(self):
        if 'website_sale_cart_quantity' not in request.session:
            return request.cart.cart_quantity
        return request.session['website_sale_cart_quantity']

    @route(
        route='/shop/cart/clear',
        type='jsonrpc',
        auth='public',
        website=True
    )
    def clear_cart(self):
        request.cart.order_line.unlink()

    def _get_cart_notification_information(self, order, added_qty_per_line):
        """ Get the information about the sales order lines to show in the notification.

        :param sale.order order: The sales order.
        :param dict added_qty_per_line: The added qty per order line.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'currency_id': int
                'lines': [{
                    'id': int
                    'image_url': int
                    'quantity': float
                    'name': str
                    'description': str
                    'added_qty_price_total': float
                }],
            }
        """
        lines = order.order_line.filtered(lambda line: line.id in set(added_qty_per_line))
        if not lines:
            return {}

        return {
            'currency_id': order.currency_id.id,
            'lines': [
                { # For the cart_notification
                    'id': line.id,
                    'image_url': order.website_id.image_url(line.product_id, 'image_128'),
                    'quantity': added_qty_per_line[line.id],
                    'name': line._get_line_header(),
                    'combination_name': line._get_combination_name(),
                    'description': line._get_sale_order_line_multiline_description_variants(),
                    'price_total': line.price_unit * added_qty_per_line[line.id],
                    **self._get_additional_cart_notification_information(line),
                } for line in lines
            ],
        }

    def _get_tracking_information(self, order_sudo, line_ids):
        """ Get the tracking information about the sales order lines.

        :param sale.order order: The sales order.
        :param list[int] line_ids: The ids of the lines to track.
        :rtype: dict
        :return: The tracking information.
        """
        lines = order_sudo.order_line.filtered(
            lambda line: line.id in line_ids
        ).with_context(display_default_code=False)
        return [
            {
                'item_id': line.product_id.barcode or line.product_id.id,
                'item_name': line.product_id.display_name,
                'item_category': line.product_id.categ_id.name,
                'currency': line.currency_id.name,
                'price': line.price_reduce_taxexcl,
                'discount': line.price_unit - line.price_reduce_taxexcl,
                'quantity': line.product_uom_qty,
            } for line in lines
        ]

    def _get_additional_cart_update_values(self, data):
        """ Look for extra information in a given dictionary to be included in a `_cart_add` call.

        :param dict data: A dictionary in which to look up for extra information.
        :return: addition values to be passed to `_cart_add`.
        :rtype: dict
        """
        if data.get('combo_item_id'):
            return {'combo_item_id': data['combo_item_id']}
        return {}

    def _get_additional_cart_notification_information(self, line):
        infos = {}
        # Only set the linked line id for combo items, not for optional products.
        if combo_item := line.combo_item_id:
            infos['linked_line_id'] = line.linked_line_id.id
            # To sell a product type 'combo', one doesn't need to publish all combo choices. This
            # causes an issue when public users access the image of each choice via the /web/image
            # route. To bypass this access check, we send the raw image URL if the product is
            # inaccessible to the current user.
            if (
                not combo_item.product_id.sudo(False).has_access('read')
                and combo_item.product_id.image_128
            ):
                infos['image_url'] = image_data_uri(combo_item.product_id.image_128)

        if line.product_template_id._has_multiple_uoms():
            infos['uom_name'] = line.product_uom_id.name

        return infos
