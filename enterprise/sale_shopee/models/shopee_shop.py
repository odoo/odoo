# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
from datetime import datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from odoo.addons.sale_shopee import const, utils

_logger = logging.getLogger(__name__)


class ShopeeShop(models.Model):
    _name = 'shopee.shop'
    _description = "Shopee Shop"
    _check_company_auto = True

    name = fields.Char(string="Name", required=True)
    account_id = fields.Many2one(
        string="Shopee Account",
        comodel_name='shopee.account',
        ondelete='cascade',
        readonly=True,
        required=True,
    )
    shopee_item_ids = fields.One2many(
        string="Shopee Items", comodel_name='shopee.item', inverse_name='shop_id'
    )

    # Credentials fields.
    shop_identifier = fields.Integer(string="Shopee Shop ID", readonly=True, required=True)
    access_token = fields.Char(
        help="Access Token expires in 4 hours and is used to access the Shopee API.",
        readonly=True,
    )
    access_token_expiration_date = fields.Datetime(
        help="Access token expiration date. Computed using the expires_in returned by Shopee.",
        readonly=True,
    )
    refresh_token = fields.Char(
        help="Refresh Token is used to request a new Access Token and expires in 30 days. Once"
             " expired, the user must re-authorize the connection on Shopee Account view.",
        readonly=True,
    )
    authorization_expiration_date = fields.Datetime(
        help="Expiration Date of Authorization of a shop, that was returned during the Shopee shop"
             " authorization on Shopee Account view. Once expired, the user must re-authorize the"
             " connection on Shopee Account view.",
        readonly=True,
    )

    # Follow-up fields.
    user_id = fields.Many2one(
        string="Default Salesperson",
        help="The default salesperson assigned to Shopee orders",
        comodel_name='res.users',
        default=lambda self: self.env.user,
        check_company=True,
    )
    team_id = fields.Many2one(
        string="Default Sales Team",
        help="The default Sales Team assigned to Shopee orders for reporting",
        comodel_name='crm.team',
        check_company=True,
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name='res.company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    fbs_location_id = fields.Many2one(
        string="FBS Stock Location",
        help="The stock location managed by Shopee under the Fulfilled by Shopee (FBS) program.",
        comodel_name='stock.location',
        domain="[('usage', '=', 'internal')]",
        check_company=True,
    )
    active = fields.Boolean(
        string="Active",
        help="If made inactive, this account will no longer be synchronized with Shopee.",
        default=True,
        required=True,
    )
    status = fields.Selection(
        help="The shop status on Shopee."
             "- Inactive: The shop is not yet approved by Shopee."
             "- Active: The shop is active and can be synchronized with Odoo."
             "- Error: The shop is banned and cannot be synchronized with Odoo.",
        selection=[
            ('inactive', "Inactive"),
            ('active', "Active"),
            ('error', "Error"),
        ],
        readonly=True,
        default='inactive',
    )
    last_shop_status_sync_date = fields.Datetime(
        string="Last Shop Status Synchronization Date",
        help="The last time the shop status was synchronized with Shopee",
        required=True,
        default=fields.Datetime.now,
    )
    last_orders_sync_date = fields.Datetime(
        string="Last Order Synchronization Date",
        help="The last time the orders were synchronized with Shopee. Orders whose status has "
             "not changed since this date will not be created nor updated in Odoo.",
        required=True,
        default=fields.Datetime.now,
    )
    synchronize_inventory = fields.Boolean(
        string="Synchronize Inventory",
        help="Whether the available quantities of products linked to this shop are  synchronized"
             " with Shopee. Only products available in FBM or hybrid will be synchronized.",
        default=False,
    )

    # Display fields.
    order_count = fields.Integer(string="Order Count", compute='_compute_order_count')
    shopee_item_count = fields.Integer(
        string="Shopee Item Count", compute='_compute_shopee_item_count'
    )
    authorization_remaining_days = fields.Integer(
        string="Authorization Remaining Days",
        help="Remaining days of the shop authorization. Show a warning in the Shopee Shop view "
             "that the authorization will expire soon.",
        compute='_compute_authorization_remaining_days',
        readonly=True,
    )

    # === COMPUTE METHODS === #

    def _compute_order_count(self):
        for shop in self:
            order_count = self.env['sale.order'].search_count([('shopee_shop_id', '=', shop.id)])
            shop.order_count = order_count

    @api.depends('shopee_item_ids')
    def _compute_shopee_item_count(self):
        for shop in self:
            shop.shopee_item_count = len(shop.shopee_item_ids)

    @api.depends('authorization_expiration_date')
    def _compute_authorization_remaining_days(self):
        for shop in self:
            if shop.authorization_expiration_date:
                shop.authorization_remaining_days = (
                    shop.authorization_expiration_date - fields.Datetime.now()
                ).days
            else:
                shop.authorization_remaining_days = -1

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        """ Associate a shop with a location and a sales team.

        By default, each shop has its own location, while all shops share the same sales team.
        """
        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            # Find or create the shopee warehouse to be associated with this account
            parent_warehouse = self.env['stock.warehouse'].search_read(
                self.env['stock.warehouse']._check_company_domain(company_id),
                ['view_location_id'],
                limit=1,
            )
            location_name = _("Shopee Warehouse - %(shop)s", shop=vals.get('name'))
            if parent_warehouse:
                location = self.env['stock.location'].search(
                    [
                        *self.env['stock.location']._check_company_domain(company_id),
                        ('name', '=', location_name),
                        ('location_id', '=', parent_warehouse[0]['view_location_id'][0]),
                    ],
                    limit=1,
                )
                if not location:
                    location = self.env['stock.location'].create({
                        'name': location_name,
                        'usage': 'internal',
                        'location_id': parent_warehouse[0]['view_location_id'][0],
                        'company_id': company_id,
                    })
                vals['fbs_location_id'] = location.id

        return super().create(vals_list)

    def write(self, vals):
        """ Override to block the change of the company of a Shopee shop."""
        if 'company_id' in vals:
            raise UserError(_("Changing the company of a Shopee shop is not allowed."))
        return super().write(vals)

    # === ACTION METHODS === #

    def action_sync_orders(self):
        self._sync_orders()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_sync_pickings(self):
        return self.env['stock.picking']._sync_shopee_pickings(tuple(self.ids))

    def action_sync_inventory(self):
        self._sync_inventory()

    def action_force_update_shop(self):
        return self._update_shop_information(force_update=True)

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sale Orders"),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('shopee_shop_id', '=', self.id)],
        }

    def action_view_shopee_items(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Shopee Items"),
            'res_model': 'shopee.item',
            'view_mode': 'list,form',
            'domain': [('shop_id', '=', self.id)],
            'context': {'default_shop_id': self.id},
        }

    def action_archive(self):
        """ Override to disconnect the Shopee shops before archiving it. """
        for shop in self:
            shop._reset_tokens()
        return super().action_archive()

    # === BUSINESS METHODS === #

    def create_or_update_shop(self, company_id, account_id, shop_id, shop_vals):
        """ Create or update a shop with the provided shop_id and account_id.

        :param int company_id: The company identifier.
        :param int account_id: The Shopee account identifier.
        :param int shop_id: The Shopee shop identifier.
        :param dict shop_vals: The values to update the shop with.
        :return: shopee.shop
        """
        shop = self.search(
            [('shop_identifier', '=', shop_id), ('account_id', '=', account_id)], limit=1
        )

        if not shop:  # When call during the onboarding of an account (and not a shop)
            shop = self.create({
                'name': _("Shopee Shop #%(shop_id)s", shop_id=shop_id),
                'shop_identifier': shop_id,
                'account_id': account_id,
                'company_id': company_id,
                **shop_vals,  # Contains the tokens from the account
            })
        else:
            if shop_vals:
                shop.write(shop_vals)
            utils.request_access_token(shop)

        shop._update_shop_information(force_update=True)
        return shop

    def _update_shop_information(self, force_update=False):
        """ Update the shop information from Shopee.

        See https://open.shopee.com/documents/v2/v2.shop.get_shop_info?module=92&type=1
        """
        self.ensure_one()

        task_begin_datetime = fields.Datetime.now()
        if force_update \
           or not self.authorization_expiration_date \
           or not self.last_shop_status_sync_date \
           or self.last_shop_status_sync_date < task_begin_datetime - timedelta(days=1):
            shop_data = utils.make_shopee_api_request(self, 'get_shop_info')
            expiration_date = datetime.fromtimestamp(shop_data['expire_time'])
            self.update({
                'status': const.SHOP_STATUS_MAPPING.get(shop_data['status'], 'error'),
                'authorization_expiration_date': expiration_date,
                'last_shop_status_sync_date': task_begin_datetime,
            })

        return self

    def _sync_orders(self, auto_commit=True):
        """ Synchronize the shops' sales orders that were recently updated on Shopee.

        If called on an empty recordset, the orders of all active shops are synchronized instead.

        Note: This method is called by the `ir_cron_sync_shopee_orders` cron.

        :param bool auto_commit: Whether the database cursor should be committed as soon as an order
                                 is successfully synchronized.
        :return: None
        """
        shops = self or self.search([])
        for shop in shops:
            shop._update_shop_information()
            if shop.status != 'active':
                continue

            start_sync_dt = fields.Datetime.now()

            try:
                # Orders are pulled in batches of up to ORDER_LIST_SIZE_LIMIT orders. If more can be
                # synchronized, the request results are paginated and the next page holds another
                # batch.
                while shop.last_orders_sync_date < start_sync_dt:
                    status_update_lower_limit = shop.last_orders_sync_date
                    status_update_upper_limit = min(
                        status_update_lower_limit + timedelta(days=const.ORDER_LIST_DAYS_LIMIT),
                        start_sync_dt,
                    )
                    order_list = shop._fetch_order_list(
                        time_from=status_update_lower_limit, time_to=status_update_upper_limit
                    )
                    if not order_list:
                        shop.last_orders_sync_date = status_update_upper_limit
                        continue

                    orders_detail = shop._fetch_orders_detail(order_list)
                    # As we fetched these orders based on their id, not their updated time, orders
                    # might have been updated later than the set upper limit. We discard them for
                    # now to avoid skipping the intermediary orders by setting a wrong last updated
                    # time as they'll be sync later anyway.
                    upper_limit_timestamp = int(status_update_upper_limit.timestamp())
                    valid_orders_detail = [
                        od for od in orders_detail if od['update_time'] <= upper_limit_timestamp
                    ]
                    if not valid_orders_detail:
                        shop.last_orders_sync_date = status_update_upper_limit
                        continue

                    for order_data in valid_orders_detail:
                        try:
                            if auto_commit:
                                with self.env.cr.savepoint():
                                    shop._process_order_data(order_data)
                            else:  # Avoid the savepoint in testing
                                shop._process_order_data(order_data)
                        except utils.ShopeeRateLimitError:
                            raise
                        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                            shopee_order_ref = order_data['order_sn']
                            _logger.info(
                                "A concurrency error occurred while processing the order data "
                                "with shopee_order_ref %(order_ref)s for Shopee shop id %(id)s."
                                " Discarding the error to trigger the retry mechanism.",
                                {'order_ref': shopee_order_ref, 'id':shop.id},
                            )
                            # Let the error bubble up so that either the request can be retried
                            # up to 5 times or the cron job rollbacks the cursor and reschedules
                            # itself later, depending on which of the two called this method.
                            raise
                        except Exception as error:
                            shopee_order_ref = order_data['order_sn']
                            _logger.warning(
                                "A business error occurred while processing the order data"
                                " with shopee_order_ref %(order_ref)s for Shopee shop %(shop)s."
                                " Skipping the order data and moving to the next order.",
                                {'order_ref': shopee_order_ref, 'shop': shop.id},
                                exc_info=True
                            )
                            # Dismiss business errors to allow the synchronization to skip the
                            # problematic orders.
                            self.env.cr.rollback()
                            shop._handle_sync_failure(
                                flow='order_sync', shopee_order_ref=shopee_order_ref
                            )
                            continue

                        if auto_commit:
                            self.env.cr.commit()  # Commit to mitigate a potential cron kill.

                    # The sync of this orders batch went through, save the last status update time
                    valid_update_times = [order['update_time'] for order in valid_orders_detail]
                    if valid_update_times and len(orders_detail) == const.ORDER_DETAIL_SIZE_LIMIT:
                        shop.last_orders_sync_date = datetime.fromtimestamp(max(valid_update_times))
                    else:
                        shop.last_orders_sync_date = status_update_upper_limit

            except utils.ShopeeRateLimitError as error:
                _logger.info(
                    "Rate limit reached while synchronizing sales orders for Shopee account with"
                    " id %(account)d. Operation: %(error_operation)s",
                    {'account': shop.account_id.id, 'error_operation': error.operation},
                )
                continue  # The remaining orders will be pulled in the next cron run.

    def _fetch_order_list(self, time_from, time_to):
        """ Fetch the order list from Shopee.

        :param datetime time_from: Lower limit for pulling orders.
        :param datetime time_to: Upper limit for pulling orders.
        :return: A list composed of Shopee's orders' unique identifiers.
        :rtype: list
        """
        response = utils.make_shopee_api_request(self, 'get_order_list', {
            'time_range_field': 'update_time',
            'time_from': int(time_from.timestamp()),
            'time_to': int(time_to.timestamp()),
            'page_size': const.ORDER_LIST_SIZE_LIMIT,
            'cursor': 0,
        })
        order_sn_list = [order['order_sn'] for order in response['order_list'] or []]
        return order_sn_list

    def _fetch_orders_detail(self, order_sn_list):
        """ Fetches the order details from Shopee.

        :param list order_sn_list: A list composed of Shopee's orders' unique identifiers.
        :return: The orders detail.
        :rtype: list
        """
        # Slicing the order list in multiple batches of fewer orders than ORDER_DETAIL_SIZE_LIMIT
        batches = [order_sn_list[i:i + const.ORDER_DETAIL_SIZE_LIMIT] for i in range(
            0, len(order_sn_list), const.ORDER_DETAIL_SIZE_LIMIT
        )]
        fields_to_fetch = [
            'buyer_user_id', 'buyer_username', 'estimated_shipping_fee', 'recipient_address',
            'actual_shipping_fee', 'item_list', 'actual_shipping_fee_confirmed',
            'fulfillment_flag', 'package_list', 'shipping_carrier', 'total_amount'
        ]
        fields_to_fetch = ','.join(fields_to_fetch)
        orders_detail = []
        for batch in batches:
            response = utils.make_shopee_api_request(
                self,
                'get_order_detail',
                {'order_sn_list': ','.join(batch), 'response_optional_fields': fields_to_fetch},
            )
            orders_detail += response.get('order_list', [])

        return orders_detail

    def _process_order_data(self, order_data):
        """ Process the provided order details and return the matching sales order, if any.

        - If the order doesn't exist in Odoo and order status in const.ORDER_STATUSES_TO_SYNC, an
        order will be created with the data from Shopee.
        - If the order exists in Odoo, depending on the status:
            -> Status = "CANCELLED" -> we cancel the order in Odoo if it's not already cancelled.
            -> Status = "SHIPPED"/"COMPLETED" -> we update the status of the order in Odoo and
                                                 validate the picking.

        Note: self.ensure_one()

        :param dict order_data: The order data to process.
        :return: The matching Shopee order, if any, as a `sale.order` record.
        :rtype: recordset of `sale.order`
        """
        self.ensure_one()

        shopee_order_ref = order_data['order_sn']
        shopee_status = order_data['order_status']
        order = self.env['sale.order'].search(
            [('shopee_order_ref', '=', shopee_order_ref), ('shopee_shop_id', '=', self.id)], limit=1
        )
        fulfillment_type = const.FULFILLMENT_TYPE_MAPPING[order_data['fulfillment_flag']]
        if not order:
            if shopee_status in const.ORDER_STATUSES_TO_SYNC[fulfillment_type]:
                order = self._create_order_from_data(order_data)
                if order.shopee_fulfillment_type == 'fbs':
                    self._generate_stock_moves(order)
                elif order.shopee_fulfillment_type in ['fbm', 'hybrid']:
                    order.with_context(mail_notrack=True).action_lock()
                _logger.info(
                    "Created a new sales order with shopee_order_ref %(ref)s for Shopee shop"
                    " with id %(id)s.",
                    {'ref': shopee_order_ref, 'id': self.id},
                )
            else:
                _logger.info(
                    "Ignored Shopee order with reference %(ref)s and status %(status)s for Shopee"
                    " shop with id %(id)s.",
                    {'ref': shopee_order_ref, 'status': shopee_status, 'id': self.id},
                )
        else:  # order exists, update the status
            if shopee_status == 'CANCELLED' and order.state != 'cancel':
                order._action_cancel()
                _logger.info(
                    "Cancelled sales order with shopee_order_ref %(ref)s for Shopee shop with id"
                    " %(id)s.",
                    {'ref': shopee_order_ref, 'id': self.id},
                )
            elif shopee_status in ('SHIPPED', 'COMPLETED') and fulfillment_type != 'fbs':
                # If the order is shipped or completed in Shopee, it means Shopee identifies the
                # package as picked up by the carrier. We then mark the picking as done in Odoo.
                # This avoids fetching the shipping label again in stock picking.
                valid_picks = order.picking_ids.filtered(lambda pick: pick.state != 'cancel')
                not_stored_label = valid_picks.filtered(lambda p: p.shopee_label_status != 'stored')
                if not_stored_label:
                    not_stored_label.shopee_label_status = 'stored'
                    _logger.info(
                        "Forced label to be stored for sales order with Shopee order"
                        " reference %(ref)s and Shopee shop with id %(id)s.",
                        {'ref': shopee_order_ref, 'id': self.id},
                    )
            else:
                _logger.info(
                    "Ignored already synchronized sales order with shopee_order_ref %(ref)s for"
                    " Shopee shop with id %(id)s.",
                    {'ref': shopee_order_ref, 'id': self.id},
                )

        # Update the delivery status to keep it in sync with Shopee
        order.shopee_delivery_status = const.DELIVERY_STATUS_MAPPING.get(shopee_status, 'error')
        return order

    def _create_order_from_data(self, order_data):
        """ Create the order from data.

        :param dict order_data: A dict of order data.
        :return: The created order.
        :rtype: sale.order
        """
        shipping_code = order_data['shipping_carrier']
        shipping_product = self._find_matching_product(
            shipping_code, 'default_shipping_product', 'Shopee Shipping', 'service'
        )
        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', order_data['currency'])], limit=1
        )
        shopee_order_ref = order_data['order_sn']
        contact_partner, delivery_partner = self._find_or_create_partners_from_data(order_data)
        fiscal_position = self.env['account.fiscal.position'].with_company(
            self.company_id
        )._get_fiscal_position(contact_partner, delivery_partner)
        order_lines_values = self._prepare_order_lines_values(
            order_data, currency, fiscal_position, shipping_product
        )
        fulfillment_type = order_data['fulfillment_flag']
        order_lines = [
            Command.create(order_line_values) for order_line_values in order_lines_values
        ]
        origin = _(
            "Shopee Order %(shopee_order_ref)s at %(shop_name)s",
            shopee_order_ref=shopee_order_ref,
            shop_name=self.name,
        )
        delivery_status = const.DELIVERY_STATUS_MAPPING.get(order_data['order_status'], 'draft')
        order_vals = {
            'origin': origin,
            'state': 'sale',
            # The order is first created unlocked and later locked to trigger the creation of a
            # stock picking if fulfilled by merchant.
            'locked': fulfillment_type == 'fulfilled_by_shopee',
            'date_order': datetime.fromtimestamp(order_data['create_time']),
            'partner_id': contact_partner.id,
            'pricelist_id': self._find_or_create_pricelist(currency).id,
            'order_line': order_lines,
            'invoice_status': 'no',
            'partner_shipping_id': delivery_partner.id,
            'require_signature': False,
            'require_payment': False,
            'fiscal_position_id': fiscal_position.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'shopee_order_ref': shopee_order_ref,
            'shopee_shop_id': self.id,
            'shopee_fulfillment_type': const.FULFILLMENT_TYPE_MAPPING[fulfillment_type],
            'shopee_delivery_status': delivery_status,
        }
        if fulfillment_type == 'fulfilled_by_shopee' and self.fbs_location_id.warehouse_id:
            order_vals['warehouse_id'] = self.fbs_location_id.warehouse_id.id
        order = self.env['sale.order'].with_context(
            mail_create_nosubscribe=True
        ).with_company(self.company_id).create(order_vals)

        if order.picking_ids and shipping_code:  # The buyer chose a specific delivery method
            delivery_method = self._find_or_create_delivery_carrier(shipping_code, shipping_product)
            order.picking_ids.carrier_id = delivery_method
        return order

    def _find_matching_product(
            self, internal_reference, default_xmlid, default_name, default_type, fallback=True
    ):
        """ Find the matching product for a given internal reference.

        If no product is found for the given internal reference, we fall back on the default
        product. If the default product was deleted, we restore it.

        :param str internal_reference: The internal reference of the product to be searched.
        :param str default_xmlid: The xmlid of the default product to use as fallback.
        :param str default_name: The name of the default product to use as fallback.
        :param str default_type: The product type of the default product to use as fallback.
        :param bool fallback: Whether we should fall back to the default product when no product
            matching the provided internal reference is found.
        :return: The matching product.
        :rtype: product.product
        """
        self.ensure_one()

        product = self.env['product.product']
        if internal_reference:
            product = self.env['product.product'].search([
                *self.env['product.product']._check_company_domain(self.company_id),
                ('default_code', '=', internal_reference),
            ], limit=1)
        if not product and fallback:  # Fallback to the default product
            product = self.env.ref(f'sale_shopee.{default_xmlid}', raise_if_not_found=False) \
                      or self.env['product.product']._restore_shopee_data_product(
                          default_name, default_type, default_xmlid
                      )
        return product

    def _find_or_create_partners_from_data(self, order_data):
        """ Find or create the partners from data

        :param dict order_data: A dict of order data.
        :return: The contact partner and the delivery partner.
        :rtype: tuple(res.partner, res.partner)
        """

        def get_streets_from_full_address(address_):
            """ Town, district and street will be stored in street and street2. """
            blocks_ = address_.get('full_address').split(', ')
            for key, value in address_.items():
                if key in ['city', 'state', 'region', 'zipcode'] and value in blocks_:
                    blocks_.remove(value)
            middle_index_ = math.ceil(len(blocks_) / 2)
            street_ = ", ".join(blocks_[:middle_index_])
            street2_ = ", ".join(blocks_[middle_index_:])
            return street_, street2_ if street2_ else False

        self.ensure_one()

        shopee_order_ref = order_data['order_sn']
        shopee_buyer_identifier = order_data['buyer_user_id']
        buyer_name = order_data['buyer_username']
        shipping_address_name = order_data['recipient_address']['name']
        city = order_data['recipient_address']['city']
        street, street2 = get_streets_from_full_address(order_data['recipient_address'])
        zip_code = order_data['recipient_address']['zipcode']
        country_code = order_data['recipient_address']['region']
        state_name = order_data['recipient_address']['state']
        phone = order_data['recipient_address']['phone']
        country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
        state = self.env['res.country.state']
        if country and state_name:
            state = self.env['res.country.state'].search([
                ('name', '=ilike', state_name),  # shopee can return a state name in capital letters
                ('country_id', '=', country.id),
            ], limit=1)
        partner_vals = {
            'street': street,
            'street2': street2,
            'zip': zip_code,
            'city': city,
            'country_id': country.id if country else False,
            'state_id': state.id if state else False,
            'phone': phone,
            'customer_rank': 1,
            'company_id': self.company_id.id,
            'shopee_buyer_identifier': shopee_buyer_identifier,
        }

        # The contact partner is searched based on all the personal information and only if the
        # user id of the buyer is provided. A match thus only occurs if the customer had already
        # made a previous order and if the personal information provided by the API did not change
        # in the meantime. If there is no match, a new contact partner is created. This behavior is
        # preferred over updating the personal information with new values because it allows using
        # the correct contact details when invoicing the customer for an earlier order, should there
        # be a change in the personal information.
        contact = self.env['res.partner'].search([
            *self.env['product.pricelist']._check_company_domain(self.company_id),
            ('type', '=', 'contact'),
            ('name', '=', buyer_name),
            ('shopee_buyer_identifier', '=', shopee_buyer_identifier),
        ], limit=1) if shopee_buyer_identifier else None  # Don't match random partners.
        if not contact:
            contact_name = buyer_name or _("Shopee Customer #%(order_no)s", order_no=shopee_order_ref)
            contact = self.env['res.partner'].with_context(tracking_disable=True).create({
                'name': contact_name,
                **partner_vals,
            })

        # The contact partner acts as delivery partner if the address is strictly equal to that of
        # the contact partner. If not, a delivery partner is created.
        delivery = contact if (
            contact.name == shipping_address_name
            and contact.street == street
            and contact.street2 == street2
            and contact.zip == zip_code
            and contact.city == city
            and contact.country_id.id == country.id
            and contact.state_id.id == state.id
        ) else None
        if not delivery:
            delivery = self.env['res.partner'].search([
                *self.env['res.partner']._check_company_domain(self.company_id),
                ('type', '=', 'delivery'),
                ('parent_id', '=', contact.id),
                ('name', '=', shipping_address_name),
                ('street', '=', street),
                ('street2', '=', street2),
                ('zip', '=', zip_code),
                ('city', '=', city),
                ('country_id', '=', country.id),
                ('state_id', '=', state.id),
            ], limit=1)
        if not delivery:
            delivery = self.env['res.partner'].with_context(tracking_disable=True).create({
                'name': shipping_address_name,
                'type': 'delivery',
                'parent_id': contact.id,
                **partner_vals,
            })

        return contact, delivery

    def _prepare_order_lines_values(self, order_data, currency, fiscal_pos, shipping_product):
        """ Prepare the values for the order lines to create based on Shopee data.

        Note: self.ensure_one()

        :param dict order_data: The order data related to the item data.
        :param record currency: The currency of the sales order, as a `res.currency` record.
        :param record fiscal_pos: The fiscal position of the sales order, as an
                                  `account.fiscal.position` record.
        :param record shipping_product: The shipping product matching the shipping code, as a
                                        `product.product` record.
        :return: The order lines values.
        :rtype: dict
        """
        self.ensure_one()

        order_lines_values = []
        for item_data in order_data['item_list']:
            sku = item_data['item_sku'] or item_data['model_sku']
            fulfillment_type = const.FULFILLMENT_TYPE_MAPPING[order_data['fulfillment_flag']]
            shopee_item = self._find_or_create_item(
                sku, item_data['item_id'], item_data['model_id'], fulfillment_type
            )
            product_taxes = shopee_item.product_id.taxes_id._filter_taxes_by_company(
                self.company_id
            )
            # add promotion information to the description
            promotion_type = self._get_promotion_type(item_data.get('promotion_type'))
            promotion_id = item_data.get('promotion_id')
            if not promotion_id:
                description = _(
                    "[%(sku)s] %(product_name)s", sku=sku, product_name=item_data['item_name']
                )
            else:
                item_title = item_data['item_name']
                description = _(
                    '[%(sku)s] %(product_title)s\nPromotion: %(promotion_type)s - id: '
                    '%(promotion_id)d',
                    sku=sku,
                    product_title=item_title,
                    promotion_type=promotion_type,
                    promotion_id=promotion_id,
                )
            quantity = item_data['model_quantity_purchased']
            original_subtotal = quantity * item_data['model_original_price']
            discounted_subtotal = quantity * item_data['model_discounted_price']

            taxes = fiscal_pos.map_tax(product_taxes)
            subtotal = self._recompute_subtotal(
                discounted_subtotal, taxes, currency
            )
            order_lines_values.append(self._convert_to_order_line_values(
                product_id=shopee_item.product_id.id,
                description=description,
                tax_ids=taxes.ids,
                original_subtotal=original_subtotal,
                subtotal=subtotal,
                quantity=quantity,
            ))

        return order_lines_values

    def _find_or_create_item(self, sku, item_identifier, model_identifier, fulfillment_type='fbm'):
        """ Find or create the shopee item based on the SKU and shop.

        Note: self.ensure_one()

        :param str sku: The SKU of the product.
        :param str item_identifier: The Shopee item identifier.
        :param str model_identifier: The Shopee model identifier.
        :param str fulfillment_type: The fulfillment type of the item.
        :return: The found or created shopee item
        :rtype: shopee.item
        """
        self.ensure_one()
        sync_to_shopee = fulfillment_type in ['fbm', 'hybrid']
        shopee_item = self.shopee_item_ids.filtered(
            lambda i: i.shopee_item_identifier == str(item_identifier)
        )
        if model_identifier:
            shopee_item = shopee_item.filtered(
                lambda i: i.shopee_model_identifier == str(model_identifier)
            )
        if not shopee_item:
            shopee_item = self.env['shopee.item'].with_context(tracking_disable=True).create({
                'product_id': self._find_matching_product(
                    sku, 'default_sale_product', 'Shopee Sales', 'consu'
                ).id,
                'shop_id': self.id,
                'shopee_item_identifier': item_identifier,
                'shopee_model_identifier': model_identifier,
                'sync_to_shopee': sync_to_shopee,
            })
        # If the item has been linked with the default product, search if another product has now
        # been assigned the current SKU as internal reference and update the item if so.
        # This trades off a bit of performance in exchange for a more expected behavior for the
        # matching of products if one was assigned the right SKU after that the item was created.
        elif 'sale_shopee.default_sale_product' in shopee_item.product_id._get_external_ids().get(
            shopee_item.product_id.id, []
        ):
            product = self._find_matching_product(sku, '', '', '', fallback=False)
            if product:
                shopee_item.product_id = product.id

        return shopee_item

    def _get_promotion_type(self, promotion_type):
        """ Get the promotion type from the promotion type mapping.

        :param str promotion_type: The promotion type.
        :return: The promotion type.
        :rtype: str
        """
        promotion_type_mapping = {
            'product_promotion': _("Product Promotion"),
            'flash_sale': _("Flash Sale"),
            'bundle_deal': _("Bundle Deal"),
            'add_on_deal_main': _("Add-on Deal Main"),
            'add_on_deal_sub': _("Add-on Deal Sub"),
        }
        return promotion_type_mapping.get(promotion_type, _("Unknown Promotion Type"))

    def _recompute_subtotal(self, total, taxes, currency):
        """ Compute the subtotal from the taxes.

        Shopee does not include tax amount of the order, we need to recompute the subtotal from the
        taxes on the product (or those given by the fiscal position) to match the order total.

        To achieve this, the subtotal is recomputed from the taxes for the total to match that of
        the order. If the taxes used are not identical to those used by Shopee, the
        recomputed subtotal will differ from the original subtotal.

        :param float total: The original total.
        :param account.tax taxes: The final taxes to use for the computation of the new subtotal.
        :param res.currency currency: The currency used by the rounding methods.
        :return: The new subtotal.
        :rtype: float
        """
        taxes_res = taxes.with_context(force_price_include=True).compute_all(
            total, currency=currency
        )
        subtotal = taxes_res['total_excluded']
        for tax_res in taxes_res['taxes']:
            tax = self.env['account.tax'].browse(tax_res['id'])
            if tax.price_include:
                subtotal += tax_res['amount']
        return subtotal

    def _convert_to_order_line_values(self, **kwargs):
        """ Convert and complete a dict of values to comply with fields of `sale.order.line`.

        :param dict kwargs: The values to convert and complete.
        :return: The completed values.
        :rtype: dict
        """
        subtotal = kwargs.get('subtotal', 0)
        quantity = kwargs.get('quantity', 1)
        original_subtotal = kwargs.get('original_subtotal', 0) or subtotal
        diff = original_subtotal - subtotal
        tax_ids = kwargs.get('tax_ids')
        return {
            'name': kwargs.get('description', ''),
            'product_id': kwargs.get('product_id'),
            'price_unit': original_subtotal / quantity if quantity else 0,
            'tax_id': tax_ids if tax_ids else [],
            'product_uom_qty': quantity,
            'discount': diff / original_subtotal * 100 if original_subtotal else 0,
        }

    def _find_or_create_pricelist(self, currency):
        """ Find or create the pricelist.

        :param res.currency currency: The currency of the pricelist
        :rtype: product.pricelist
        """
        self.ensure_one()
        pricelist = self.env['product.pricelist'].with_context(active_test=False).search([
            *self.env['product.pricelist']._check_company_domain(self.company_id),
            ('currency_id', '=', currency.id),
        ], limit=1)
        if not pricelist:
            pricelist = self.env['product.pricelist'].with_context(tracking_disable=True).create({
                'name': _("Shopee Pricelist %(currency)s", currency=currency.name),
                'active': False,
                'currency_id': currency.id,
                'company_id': self.company_id.id,
            })
        return pricelist

    def _find_or_create_delivery_carrier(self, shipping_code, shipping_product):
        """ Find or create a delivery carrier based on the shipping code.

        :param str shipping_code: The shipping code.
        :param record shipping_product: The shipping product matching the shipping code, as a
                                        `product.product` record.
        :return: The delivery carrier.
        :rtype: delivery.carrier
        """
        delivery_method = self.env['delivery.carrier'].search(
            [('name', '=', shipping_code)], limit=1,
        )
        if not delivery_method:
            delivery_method = self.env['delivery.carrier'].create({
                'name': shipping_code, 'product_id': shipping_product.id
            })
        return delivery_method

    def _generate_stock_moves(self, order):
        """ Generate a stock move for each product of the provided sales order.

        :param sale.order order: The sales order to generate stock moves.
        :return: The generated stock moves.
        :rtype: stock.move
        """
        customers_location = self.env.ref('stock.stock_location_customers')
        for order_line in order.order_line.filtered(lambda l: l.product_id.type == 'consu'):
            stock_move = self.env['stock.move'].create({
                'name': _("Shopee move: %(name)s", name=order.name),
                'company_id': self.company_id.id,
                'product_id': order_line.product_id.id,
                'product_uom_qty': order_line.product_uom_qty,
                'product_uom': order_line.product_uom.id,
                'location_id': self.fbs_location_id.id,
                'location_dest_id': customers_location.id,
                'state': 'confirmed',
                'sale_line_id': order_line.id,
            })
            stock_move._set_quantity_done(order_line.product_uom_qty)
            stock_move.picked = True  # To also change move lines created in `_set_quantity_done`
            stock_move._action_done()

    def _handle_sync_failure(self, flow='', shopee_order_ref=False, error_messages=False):
        """ Send a mail to the responsible persons to report a synchronization failure.

        :param str flow: The flow for which the failure mail is requested. Supported flows are:
                        `order_sync`, `inventory_sync`, and `picking_sync`.
        :param str shopee_order_ref: The shopee references of the orders that failed to synchronize.
        :param list[dict] error_messages: A list containing the referenced Shopee orders and their
                                          linked errors in the format [{"order_ref": "error"}].
                                          Required for the `picking_sync` flow.
        :return: None
        """
        if flow == 'order_sync':
            _logger.exception(
                "Failed to synchronize order with shopee reference %(ref)s for shopee.shop with "
                "id %(shop_id)s (Shope Name: %(shop_name)s)."
                "Please create the order manually.",
                {'ref': shopee_order_ref, 'shop_id': self.id, 'shop_name': self.name},
            )
            mail_template_id = 'sale_shopee.order_sync_failure'
        elif flow == 'inventory_sync':
            _logger.exception(
                "Failed to synchronize the inventory for items in shopee.shop with id "
                "%(shop_id)s (Shope Name: %(shop_name)s).",
                {'shop_id': self.id, 'shop_name': self.name},
            )
            mail_template_id = 'sale_shopee.inventory_sync_failure'
        else:  # flow == 'picking_sync':
            _logger.exception(
                "Failed to synchronize pickings for shopee.shop with id "
                "%(shop_id)s (Shope Name: %(shop_name)s).",
                {'shop_id': self.id, 'shop_name': self.name},
            )
            mail_template_id = 'sale_shopee.picking_sync_failure'

        mail_template = self.env.ref(mail_template_id, raise_if_not_found=False)
        if not mail_template:
            _logger.warning(
                "The mail template with xmlid %(mail_template)s has been deleted.",
                {'mail_template': mail_template_id}
            )
        else:
            responsible_emails = {user.email for user in filter(
                None, (self.user_id, self.env.ref('base.user_admin', raise_if_not_found=False))
            )}
            mail_template.with_context(
                email_to=','.join(responsible_emails),
                shopee_order_ref=shopee_order_ref,
                error_messages=error_messages,
                shopee_shop=self.name,
            ).send_mail(self.env.user.id)
            _logger.info(
                "Sent synchronization failure notification email to %(emails)s",
                {'emails': ', '.join(responsible_emails)},
            )

    def _sync_inventory(self, auto_commit=True):
        """ Synchronize the inventory level of products sold on Shopee.

        If called on an empty recordset, the products of all active shops with inventory
        synchronization are synchronized instead.

        :param bool auto_commit: Whether the database cursor should be committed as soon as an item
                                 is successfully synchronized.
        :return: None
        """
        shops = self or self.search([])
        for shop in shops:
            shop._update_shop_information()
            if shop.status != 'active' or not shop.synchronize_inventory:
                continue
            shop.shopee_item_ids._sync_inventory(auto_commit)

    def _reset_tokens(self):
        self.update({
            'access_token': False,
            'access_token_expiration_date': False,
            'refresh_token': False,
            'authorization_expiration_date': False,
        })
