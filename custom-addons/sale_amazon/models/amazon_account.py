# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from datetime import timedelta

import dateutil.parser
import psycopg2
from markupsafe import Markup
from werkzeug import urls

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY as CONCURRENCY_ERRORS

from odoo.addons.sale_amazon import const, utils as amazon_utils
from odoo.addons.sale_amazon.controllers.onboarding import compute_oauth_signature


_logger = logging.getLogger(__name__)


class AmazonAccount(models.Model):
    _name = 'amazon.account'
    _description = "Amazon Account"
    _check_company_auto = True

    name = fields.Char(string="Name", help="The user-defined name of the account.", required=True)
    offer_ids = fields.One2many(
        string="Offers", comodel_name='amazon.offer', inverse_name='account_id', auto_join=True
    )

    # Credentials fields.
    seller_key = fields.Char()
    refresh_token = fields.Char(
        string="LWA Refresh Token",
        help="The long-lived token that can be exchanged for a new access token.",
    )
    # The API credentials fields below are not stored because they are all short-lived. Their values
    # are kept in memory for the duration of the request and they are re-used as long as they are
    # not expired. If that happens, they are refreshed through an API call.
    access_token = fields.Char(
        string="LWA Access Token",
        help="The short-lived token used to query Amazon API on behalf of a seller.",
        store=False,
    )
    access_token_expiry = fields.Datetime(
        string="The moment at which the token becomes invalid.", default='1970-01-01', store=False
    )
    aws_access_key = fields.Char(
        string="AWS Access Key",
        help="The short-lived key used to identify the assumed ARN role on AWS.",
        store=False,
    )
    aws_secret_key = fields.Char(
        string="AWS Secret Key",
        help="The short-lived key used to verify the access to the assumed ARN role on AWS.",
        store=False,
    )
    aws_session_token = fields.Char(
        string="AWS Session Token",
        help="The short-lived token used to query the SP-API with the assumed ARN role on AWS.",
        store=False,
    )
    aws_credentials_expiry = fields.Datetime(
        string="The moment at which the AWS credentials become invalid.",
        default='1970-01-01',
        store=False,
    )
    restricted_data_token = fields.Char(
        string="Restricted Data Token",
        help="The short-lived token used instead of the LWA Access Token to access restricted data",
        store=False,
    )
    restricted_data_token_expiry = fields.Datetime(
        string="The moment at which the Restricted Data Token becomes invalid.",
        default='1970-01-01',
        store=False,
    )

    # Marketplace fields.
    base_marketplace_id = fields.Many2one(
        string="Home Marketplace",
        help="The home marketplace of this account; used for authentication only.",
        comodel_name='amazon.marketplace',
        required=True,
    )
    available_marketplace_ids = fields.Many2many(
        string="Available Marketplaces",
        help="The marketplaces this account has access to.",
        comodel_name='amazon.marketplace',
        relation='amazon_account_marketplace_rel',
        copy=False,
    )
    active_marketplace_ids = fields.Many2many(
        string="Sync Marketplaces",
        help="The marketplaces this account sells on.",
        comodel_name='amazon.marketplace',
        relation='amazon_account_active_marketplace_rel',
        domain="[('id', 'in', available_marketplace_ids)]",
        copy=False,
    )

    # Follow-up fields.
    user_id = fields.Many2one(
        string="Salesperson",
        comodel_name='res.users',
        default=lambda self: self.env.user,
        check_company=True,
    )
    team_id = fields.Many2one(
        string="Sales Team",
        help="The Sales Team assigned to Amazon orders for reporting",
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
    location_id = fields.Many2one(
        string="Stock Location",
        help="The location of the stock managed by Amazon under the Amazon Fulfillment program.",
        comodel_name='stock.location',
        domain="[('usage', '=', 'internal')]",
        check_company=True,
    )
    active = fields.Boolean(
        string="Active",
        help="If made inactive, this account will no longer be synchronized with Amazon.",
        default=True,
        required=True,
    )
    synchronize_inventory = fields.Boolean(
        string="Synchronize FBM Inventory",
        help="Whether the available quantities of FBM products linked to this account are"
             " synchronized with Amazon.",
        default=True,
    )
    last_orders_sync = fields.Datetime(
        help="The last synchronization date for orders placed on this account. Orders whose status "
             "has not changed since this date will not be created nor updated in Odoo.",
        default=fields.Datetime.now,
        required=True,
    )

    # Display fields.
    order_count = fields.Integer(compute='_compute_order_count')
    offer_count = fields.Integer(compute='_compute_offer_count')
    is_follow_up_displayed = fields.Boolean(compute='_compute_is_follow_up_displayed')

    #=== COMPUTE METHODS ===#

    def _compute_order_count(self):
        for account in self:
            account.order_count = self.env['sale.order.line'].search_count([('amazon_offer_id.account_id', '=', account.id)])

    def _compute_offer_count(self):
        offers_data = self.env['amazon.offer']._read_group(
            [('account_id', 'in', self.ids)], ['account_id'], ['__count']
        )
        accounts_data = {account.id: count for account, count in offers_data}
        for account in self:
            account.offer_count = accounts_data.get(account.id, 0)

    @api.depends('company_id')  # Trick to compute the field on new records
    def _compute_is_follow_up_displayed(self):
        """ Return True is the page Order Follow-up should be displayed in the view form. """
        for account in self:
            account.is_follow_up_displayed = account._origin.id or self.user_has_groups(
                'base.group_multi_company,base.group_no_one'
            )

    #=== ONCHANGE METHODS ===#

    @api.onchange('last_orders_sync')
    def _onchange_last_orders_sync(self):
        """ Display a warning about the possible consequences of modifying the last orders sync. """
        self.ensure_one()
        if self._origin.id:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _("If the date is set in the past, orders placed on this Amazon "
                                 "Account before the first synchronization of the module might be "
                                 "synchronized with Odoo.\n"
                                 "If the date is set in the future, orders placed on this Amazon "
                                 "Account between the previous and the new date will not be "
                                 "synchronized with Odoo.")
                }
            }

    #=== CONSTRAINT METHODS ===#

    @api.constrains('active_marketplace_ids')
    def _check_actives_subset_of_availables(self):
        for account in self:
            if account.active_marketplace_ids.filtered(
                    lambda m: m.id not in account.available_marketplace_ids.ids):
                raise exceptions.ValidationError(_("Only available marketplaces can be selected"))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        amazon_accounts_rg = self._read_group([], ['team_id', 'location_id'])
        amazon_teams_ids = [team.id for team, __ in amazon_accounts_rg]
        amazon_locations_ids = [location.id for __, location in amazon_accounts_rg]
        for vals in vals_list:
            # Find or create the location of the Amazon warehouse to be associated with this account
            location = self.env['stock.location'].search([
                *self.env['stock.location']._check_company_domain(vals.get('company_id')),
                ('id', 'in', amazon_locations_ids),
            ], limit=1)
            if not location:
                parent_location_data = self.env['stock.warehouse'].search_read(
                    [*self.env['stock.warehouse']._check_company_domain(vals.get('company_id'))],
                    ['view_location_id'],
                    limit=1,
                )
                location = self.env['stock.location'].create({
                    'name': 'Amazon',
                    'usage': 'internal',
                    'location_id': parent_location_data[0]['view_location_id'][0],
                    'company_id': vals.get('company_id'),
                })
            vals.update({'location_id': location.id})

            # Find or create the sales team to be associated with this account
            team = self.env['crm.team'].search([
                *self.env['crm.team']._check_company_domain(vals.get('company_id')),
                ('id', 'in', amazon_teams_ids),
            ], limit=1)
            if not team:
                team = self.env['crm.team'].create({
                    'name': 'Amazon',
                    'company_id': vals.get('company_id'),
                })
            vals.update({'team_id': team.id})

        return super().create(vals_list)

    #=== ACTION METHODS ===#

    def action_redirect_to_oauth_url(self):
        """ Build the OAuth redirect URL and redirect the user to it.

        See step 1 of https://developer-docs.amazon.com/sp-api/docs/website-authorization-workflow.

        Note: self.ensure_one()

        :return: An `ir.actions.act_url` action to redirect the user to the OAuth URL.
        :rtype: dict
        """
        self.ensure_one()

        base_seller_central_url = self.base_marketplace_id.seller_central_url
        oauth_url = urls.url_join(base_seller_central_url, '/apps/authorize/consent')
        base_database_url = self.get_base_url()
        metadata = {
            'account_id': self.id,
            'return_url': urls.url_join(base_database_url, 'amazon/return'),
            'signature': compute_oauth_signature(self.id),
        }  # The metadata included in the redirect URL after authorizing the app on Amazon.
        oauth_url_params = {
            'application_id': const.APP_ID,
            'state': json.dumps(metadata),
        }
        return {
            'type': 'ir.actions.act_url',
            'url': f'{oauth_url}?{urls.url_encode(oauth_url_params)}',
            'target': 'self',
        }

    def action_reset_refresh_token(self):
        """ Reset the refresh token of the account.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

        self.refresh_token = None

    def action_update_available_marketplaces(self):
        """ Update available marketplaces and assign new ones to the account.

        :return: A rainbow-man action to inform the user about the successful update.
        :rtype: dict
        """
        for account in self:
            available_marketplaces = account._get_available_marketplaces()
            new_marketplaces = available_marketplaces - account.available_marketplace_ids
            account.write({'available_marketplace_ids': [(6, 0, available_marketplaces.ids)]})
            # Remove active marketplace that are no longer available
            account.active_marketplace_ids &= account.available_marketplace_ids
            account.active_marketplace_ids += new_marketplaces
        return {
            'effect': {
                'type': 'rainbow_man',
                'message': _("Successfully updated the marketplaces available to this account!"),
            }
        }

    def action_view_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Offers'),
            'res_model': 'amazon.offer',
            'view_mode': 'tree',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def action_view_orders(self):
        self.ensure_one()
        order_lines = self.env['sale.order.line'].search(
            [('amazon_offer_id', '!=', False), ('amazon_offer_id.account_id', '=', self.id)]
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', order_lines.order_id.ids)],
            'context': {'create': False},
        }

    def action_sync_orders(self):
        self._sync_orders()

    def action_sync_pickings(self):
        self.env['stock.picking']._sync_pickings(tuple(self.ids))

    def action_sync_inventory(self):
        self._sync_inventory()

    def action_sync_feeds_status(self):
        self._sync_feeds()

    def action_recover_order(self):
        self.ensure_one()
        return {
            'name': _("Recover Order"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'amazon.recover.order.wizard',
            'target': 'new',
        }

    #=== BUSINESS METHODS ===#

    def _get_available_marketplaces(self):
        """ Fetch the API refs of the available marketplaces and return the corresponding recordset.

        Note: self.ensure_one()

        :return: The available marketplaces for the Amazon account.
        :rtype: recordset of `amazon.marketplace`
        :raise UserError: If the rate limit is reached.
        """
        self.ensure_one()

        amazon_utils.ensure_account_is_set_up(self, require_marketplaces=False)
        try:
            response_content = amazon_utils.make_sp_api_request(
                self, 'getMarketplaceParticipations'
            )
        except amazon_utils.AmazonRateLimitError:
            _logger.info(
                "Rate limit reached while updating available marketplaces for Amazon account with "
                "id %s.", self.id
            )
            raise UserError(_(
                "You reached the maximum number of requests for this operation; please try again "
                "later."
            ))
        else:
            available_marketplace_api_refs = [
                marketplace['marketplace']['id'] for marketplace in response_content['payload']
            ]
            return self.env['amazon.marketplace'].search(
                [('api_ref', 'in', available_marketplace_api_refs)]
            )

    def _sync_orders(self, auto_commit=True):
        """ Synchronize the accounts' sales orders that were recently updated on Amazon.

        If called on an empty recordset, the orders of all active accounts are synchronized instead.

        Note: This method is called by the `ir_cron_sync_amazon_orders` cron.

        :param bool auto_commit: Whether the database cursor should be committed as soon as an order
                                 is successfully synchronized.
        :return: None
        """
        accounts = self or self.search([])
        for account in accounts:
            account = account[0]  # Avoid pre-fetching after each cache invalidation.
            amazon_utils.ensure_account_is_set_up(account)

            # The last synchronization date of the account is used as the lower limit on the orders'
            # last status update date. The upper limit is determined by the API and returned with
            # the request response, then saved on the account if the synchronization goes through.
            last_updated_after = account.last_orders_sync  # Lower limit for pulling orders.
            status_update_upper_limit = None  # Upper limit of synchronized orders.

            # Pull all recently updated orders and save the progress during synchronization.
            payload = {
                'LastUpdatedAfter': last_updated_after.isoformat(sep='T'),
                'MarketplaceIds': ','.join(account.active_marketplace_ids.mapped('api_ref')),
            }
            try:
                # Orders are pulled in batches of up to 100 orders. If more can be synchronized, the
                # request results are paginated and the next page holds another batch.
                has_next_page = True
                while has_next_page:
                    # Pull the next batch of orders data.
                    orders_batch_data, has_next_page = amazon_utils.pull_batch_data(
                        account, 'getOrders', payload
                    )
                    orders_data = orders_batch_data['Orders']
                    status_update_upper_limit = dateutil.parser.parse(
                        orders_batch_data['LastUpdatedBefore']
                    )

                    # Process the batch one order data at a time.
                    for order_data in orders_data:
                        try:
                            if auto_commit:
                                with self.env.cr.savepoint():
                                    account._process_order_data(order_data)
                            else:  # Avoid the savepoint in testing
                                account._process_order_data(order_data)
                        except amazon_utils.AmazonRateLimitError:
                            raise  # Don't treat a rate limit error as a business error.
                        except Exception as error:
                            amazon_order_ref = order_data['AmazonOrderId']
                            if isinstance(error, psycopg2.OperationalError) \
                                and error.pgcode in CONCURRENCY_ERRORS:
                                _logger.info(
                                    "A concurrency error occurred while processing the order data "
                                    "with amazon_order_ref %s for Amazon account with id %s. "
                                    "Discarding the error to trigger the retry mechanism.",
                                    amazon_order_ref, account.id
                                )
                                # Let the error bubble up so that either the request can be retried
                                # up to 5 times or the cron job rollbacks the cursor and reschedules
                                # itself later, depending on which of the two called this method.
                                raise
                            else:
                                _logger.warning(
                                    "A business error occurred while processing the order data "
                                    "with amazon_order_ref %s for Amazon account with id %s. "
                                    "Skipping the order data and moving to the next order.",
                                    amazon_order_ref, account.id,
                                    exc_info=True
                                )
                                # Dismiss business errors to allow the synchronization to skip the
                                # problematic orders and require synchronizing them manually.
                                self.env.cr.rollback()
                                account._handle_sync_failure(
                                    flow='order_sync', amazon_order_ref=amazon_order_ref
                                )
                                continue  # Skip these order data and resume with the next ones.

                        # The synchronization of this order went through, use its last status update
                        # as a backup and set it to be the last synchronization date of the account.
                        last_order_update = dateutil.parser.parse(order_data['LastUpdateDate'])
                        account.last_orders_sync = last_order_update.replace(tzinfo=None)
                        if auto_commit:
                            with amazon_utils.preserve_credentials(account):
                                self.env.cr.commit()  # Commit to mitigate an eventual cron kill.
            except amazon_utils.AmazonRateLimitError as error:
                _logger.info(
                    "Rate limit reached while synchronizing sales orders for Amazon account with "
                    "id %s. Operation: %s", account.id, error.operation
                )
                continue  # The remaining orders will be pulled later when the cron runs again.

            # There are no more orders to pull and the synchronization went through. Set the API
            # upper limit on order status update to be the last synchronization date of the account.
            account.last_orders_sync = status_update_upper_limit.replace(tzinfo=None)

    def _sync_order_by_reference(self, amazon_order_ref):
        """ Synchronize an order based on its Amazon order reference.

        Note: `self.ensure_one()`

        :param str amazon_order_ref: The amazon reference of the order to re-synchronize.
        :return: The synchronized Amazon order act window.
        :rtype: dict
        :raise UserError: If the order reference is incorrect or the order is not for an active
                          marketplace.
        :raise ValidationError: If the order is in a status that prevents its synchronization.
        """
        self.ensure_one()
        amazon_utils.ensure_account_is_set_up(self)

        order_data = amazon_utils.make_sp_api_request(
            self, 'getOrder', path_parameter=amazon_order_ref
        )['payload']
        if not order_data:  # Order not found by Amazon
            raise UserError(_("The provided reference does not match any Amazon order."))
        if order_data['MarketplaceId'] not in self.active_marketplace_ids.mapped('api_ref'):
            raise UserError(_("The order was not found on this account's marketplaces."))

        order = self._process_order_data(order_data)
        if not order:
            amazon_status = order_data['OrderStatus']
            fulfillment_channel = order_data['FulfillmentChannel']
            raise ValidationError(_(
                "The Amazon order with reference %(ref)s was not recovered because its status"
                " (%(status)s) is not eligible for synchronization for its fulfillment channel"
                " (%(channel)s).",
                ref=amazon_order_ref,
                status=amazon_status,
                channel=fulfillment_channel,
            ))
        return {
            'name': order.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }

    def _process_order_data(self, order_data):
        """ Process the provided order data and return the matching sales order, if any.

        If no matching sales order is found, a new one is created if it is in a 'synchronizable'
        status: 'Shipped' or 'Unshipped', if it is respectively an FBA or an FBA order. If the
        matching sales order already exists and the Amazon order was canceled, the sales order is
        also canceled. If the matching sales order already exists and the order data confirm that a
        FBM order got shipped, we update the shipping status when it's needed.

        Note: self.ensure_one()

        :param dict order_data: The order data to process.
        :return: The matching Amazon order, if any, as a `sale.order` record.
        :rtype: recordset of `sale.order`
        """
        self.ensure_one()

        # Search for the sales order based on its Amazon order reference.
        amazon_order_ref = order_data['AmazonOrderId']
        order = self.env['sale.order'].search(
            [('amazon_order_ref', '=', amazon_order_ref)], limit=1
        )
        amazon_status = order_data['OrderStatus']
        fulfillment_channel = order_data['FulfillmentChannel']
        if not order:  # No sales order was found with the given Amazon order reference.
            if amazon_status in const.STATUS_TO_SYNCHRONIZE[fulfillment_channel]:
                # Create the sales order and generate stock moves depending on the Amazon channel.
                order = self._create_order_from_data(order_data)
                if order.amazon_channel == 'fba':
                    self._generate_stock_moves(order)
                elif order.amazon_channel == 'fbm':
                    order.with_context(mail_notrack=True).action_lock()
                _logger.info(
                    "Created a new sales order with amazon_order_ref %(ref)s for Amazon account"
                    " with id %(id)s.", {'ref': amazon_order_ref, 'id': self.id}
                )
            else:
                _logger.info(
                    "Ignored Amazon order with reference %(ref)s and status %(status)s for Amazon"
                    " account with id %(account_id)s.",
                    {'ref': amazon_order_ref, 'status': amazon_status, 'account_id': self.id},
                )
        else:  # The sales order already exists.
            unsynced_pickings = order.picking_ids.filtered(
                lambda picking: picking.amazon_sync_status != 'done' and picking.state != 'cancel'
            )  # Consider any "unsynced" status so that we synchronize updates made from Amazon.
            if amazon_status == 'Canceled' and order.state != 'cancel':
                order._action_cancel()
                _logger.info(
                    "Canceled sales order with amazon_order_ref %(ref)s for Amazon account with id"
                    " %(id)s.", {'ref': amazon_order_ref, 'id': self.id}
                )
            elif amazon_status == 'Shipped' and fulfillment_channel == 'MFN' and unsynced_pickings:
                # The processing of the feed of a batch of pickings can fail on Amazon side in a way
                # that we cannot tell which picking is faulty. In that case, all pickings of the
                # batch are flagged as in error. The order status update allows correcting the
                # status of non-faulty pickings while leaving the faulty one in error.
                unsynced_pickings.amazon_sync_status = 'done'
                _logger.info(
                    "Forced the picking synchronization status to 'done' for sales order with"
                    " Amazon order reference %(ref)s and Amazon account with id %(id)s.",
                    {'ref': amazon_order_ref, 'id': self.id},
                )
            else:
                _logger.info(
                    "Ignored already synchronized sales order with amazon_order_ref %(ref)s for"
                    " Amazon account with id %(id)s.", {'ref': amazon_order_ref, 'id': self.id}
                )
        return order

    def _create_order_from_data(self, order_data):
        """ Create a new sales order based on the provided order data.

        Note: self.ensure_one()

        :param dict order_data: The order data to create a sales order from.
        :return: The newly created sales order.
        :rtype: record of `sale.order`
        """
        self.ensure_one()

        # Prepare the order line values.
        shipping_code = order_data.get('ShipServiceLevel')
        shipping_product = self._find_matching_product(
            shipping_code, 'shipping_product', 'Shipping', 'service'
        )
        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', order_data['OrderTotal']['CurrencyCode'])], limit=1
        )
        amazon_order_ref = order_data['AmazonOrderId']
        contact_partner, delivery_partner = self._find_or_create_partners_from_data(order_data)
        fiscal_position = self.env['account.fiscal.position'].with_company(
            self.company_id
        )._get_fiscal_position(contact_partner, delivery_partner)
        order_lines_values = self._prepare_order_lines_values(
            order_data, currency, fiscal_position, shipping_product
        )

        # Create the sales order.
        fulfillment_channel = order_data['FulfillmentChannel']
        purchase_date = dateutil.parser.parse(order_data['PurchaseDate']).replace(tzinfo=None)
        order_vals = {
            'origin': f"Amazon Order {amazon_order_ref}",
            'state': 'sale',
            # The order is first created unlocked and later locked to trigger the creation of a
            # stock picking if fulfilled by merchant.
            'locked': fulfillment_channel == 'AFN',
            'date_order': purchase_date,
            'partner_id': contact_partner.id,
            'pricelist_id': self._find_or_create_pricelist(currency).id,
            'order_line': [(0, 0, order_line_values) for order_line_values in order_lines_values],
            'invoice_status': 'no',
            'partner_shipping_id': delivery_partner.id,
            'require_signature': False,
            'require_payment': False,
            'fiscal_position_id': fiscal_position.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'amazon_order_ref': amazon_order_ref,
            'amazon_channel': 'fba' if fulfillment_channel == 'AFN' else 'fbm',
        }
        if fulfillment_channel == 'AFN' and self.location_id.warehouse_id:
            order_vals['warehouse_id'] = self.location_id.warehouse_id.id
        return self.env['sale.order'].with_context(
            mail_create_nosubscribe=True
        ).with_company(self.company_id).create(order_vals)

    def _find_or_create_partners_from_data(self, order_data):
        """ Find or create the contact and delivery partners based on the provided order data.

        Note: self.ensure_one()

        :param dict order_data: The order data to find or create the partners from.
        :return: The contact and delivery partners, as `res.partner` records. When the contact
                 partner acts as delivery partner, the records are the same.
        :rtype: tuple[record of `res.partner`, record of `res.partner`]
        """
        self.ensure_one()

        amazon_order_ref = order_data['AmazonOrderId']
        anonymized_email = order_data['BuyerInfo'].get('BuyerEmail', '')
        buyer_name = order_data['BuyerInfo'].get('BuyerName', '')
        shipping_address_info = order_data.get('ShippingAddress', {})
        shipping_address_name = shipping_address_info.get('Name', '')
        street = shipping_address_info.get('AddressLine1', '')
        address_line2 = shipping_address_info.get('AddressLine2', '')
        address_line3 = shipping_address_info.get('AddressLine3', '')
        street2 = "%s %s" % (address_line2, address_line3) if address_line2 or address_line3 \
            else None
        zip_code = shipping_address_info.get('PostalCode', '')
        city = shipping_address_info.get('City', '')
        country_code = shipping_address_info.get('CountryCode', '')
        state_code = shipping_address_info.get('StateOrRegion', '')
        phone = shipping_address_info.get('Phone', '')
        is_company = shipping_address_info.get('AddressType') == 'Commercial'
        country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
        state = self.env['res.country.state'].search([
            ('country_id', '=', country.id),
            '|', ('code', '=ilike', state_code), ('name', '=ilike', state_code),
        ], limit=1)
        if country and not state:  # avoid trying to create a state with a nonexistent country
            state = self.env['res.country.state'].with_context(tracking_disable=True).create({
                'country_id': country.id, 'name': state_code, 'code': state_code
            })
        partner_vals = {
            'street': street,
            'street2': street2,
            'zip': zip_code,
            'city': city,
            'country_id': country.id,
            'state_id': state.id,
            'phone': phone,
            'customer_rank': 1,
            'company_id': self.company_id.id,
            'amazon_email': anonymized_email,
        }

        # The contact partner is searched based on all the personal information and only if the
        # amazon email is provided. A match thus only occurs if the customer had already made a
        # previous order and if the personal information provided by the API did not change in the
        # meantime. If there is no match, a new contact partner is created. This behavior is
        # preferred over updating the personal information with new values because it allows using
        # the correct contact details when invoicing the customer for an earlier order, should there
        # be a change in the personal information.
        contact = self.env['res.partner'].search([
            *self.env['res.partner']._check_company_domain(self.company_id),
            ('type', '=', 'contact'),
            ('name', '=', buyer_name),
            ('amazon_email', '=', anonymized_email),
        ], limit=1) if anonymized_email else None  # Don't match random partners.
        if not contact:
            contact_name = buyer_name or f"Amazon Customer # {amazon_order_ref}"
            contact = self.env['res.partner'].with_context(tracking_disable=True).create({
                'name': contact_name,
                'is_company': is_company,
                **partner_vals,
            })

        # The contact partner acts as delivery partner if the address is strictly equal to that of
        # the contact partner. If not, a delivery partner is created.
        delivery = contact if (
            contact.name == shipping_address_name
            and contact.street == street
            and (not contact.street2 or contact.street2 == street2)
            and contact.zip == zip_code
            and contact.city == city
            and contact.country_id.id == country.id
            and contact.state_id.id == state.id
        ) else None
        if not delivery:
            delivery = self.env['res.partner'].search([
                *self.env['res.partner']._check_company_domain(self.company_id),
                ('parent_id', '=', contact.id),
                ('type', '=', 'delivery'),
                ('name', '=', shipping_address_name),
                ('street', '=', street),
                '|', ('street2', '=', False), ('street2', '=', street2),
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
        """ Prepare the values for the order lines to create based on Amazon data.

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
        def pull_items_data(amazon_order_ref_):
            """ Pull all item data for the order to synchronize.

            :param str amazon_order_ref_: The Amazon reference of the order to synchronize.
            :return: The items data.
            :rtype: list
            """
            items_data_ = []
            # Order items are pulled in batches. If more order items than those returned can be
            # synchronized, the request results are paginated and the next page holds another batch.
            has_next_page_ = True
            while has_next_page_:
                # Pull the next batch of order items.
                items_batch_data_, has_next_page_ = amazon_utils.pull_batch_data(
                    self, 'getOrderItems', {}, path_parameter=amazon_order_ref_
                )
                items_data_ += items_batch_data_['OrderItems']
            return items_data_

        def convert_to_order_line_values(**kwargs_):
            """ Convert and complete a dict of values to comply with fields of `sale.order.line`.

            :param dict kwargs_: The values to convert and complete.
            :return: The completed values.
            :rtype: dict
            """
            subtotal_ = kwargs_.get('subtotal', 0)
            quantity_ = kwargs_.get('quantity', 1)
            return {
                'name': kwargs_.get('description', ''),
                'product_id': kwargs_.get('product_id'),
                'price_unit': subtotal_ / quantity_ if quantity_ else 0,
                'tax_id': [(6, 0, kwargs_.get('tax_ids', []))],
                'product_uom_qty': quantity_,
                'discount': (kwargs_.get('discount', 0) / subtotal_) * 100 if subtotal_ else 0,
                'display_type': kwargs_.get('display_type', False),
                'amazon_item_ref': kwargs_.get('amazon_item_ref'),
                'amazon_offer_id': kwargs_.get('amazon_offer_id'),
            }

        self.ensure_one()

        amazon_order_ref = order_data['AmazonOrderId']
        marketplace_api_ref = order_data['MarketplaceId']

        items_data = pull_items_data(amazon_order_ref)

        order_lines_values = []
        for item_data in items_data:
            # Prepare the values for the product line.
            sku = item_data['SellerSKU']
            marketplace = self.active_marketplace_ids.filtered(
                lambda m: m.api_ref == marketplace_api_ref
            )
            offer = self._find_or_create_offer(sku, marketplace)
            product_taxes = offer.product_id.taxes_id.filtered_domain(
                [*self.env['account.tax']._check_company_domain(self.company_id)]
            )
            main_condition = item_data.get('ConditionId')
            sub_condition = item_data.get('ConditionSubtypeId')
            if not main_condition or main_condition.lower() == 'new':
                description = "[%s] %s" % (sku, item_data['Title'])
            else:
                item_title = item_data['Title']
                description = _(
                    "[%s] %s\nCondition: %s - %s", sku, item_title, main_condition, sub_condition
                )
            sales_price = float(item_data.get('ItemPrice', {}).get('Amount', 0.0))
            tax_amount = float(item_data.get('ItemTax', {}).get('Amount', 0.0))
            original_subtotal = sales_price - tax_amount \
                if marketplace.tax_included else sales_price
            taxes = fiscal_pos.map_tax(product_taxes) if fiscal_pos else product_taxes
            subtotal = self._recompute_subtotal(
                original_subtotal, tax_amount, taxes, currency, fiscal_pos
            )
            promo_discount = float(item_data.get('PromotionDiscount', {}).get('Amount', '0'))
            promo_disc_tax = float(item_data.get('PromotionDiscountTax', {}).get('Amount', '0'))
            original_promo_discount_subtotal = promo_discount - promo_disc_tax \
                if marketplace.tax_included else promo_discount
            promo_discount_subtotal = self._recompute_subtotal(
                original_promo_discount_subtotal, promo_disc_tax, taxes, currency, fiscal_pos
            )
            amazon_item_ref = item_data['OrderItemId']
            order_lines_values.append(convert_to_order_line_values(
                product_id=offer.product_id.id,
                description=description,
                subtotal=subtotal,
                tax_ids=taxes.ids,
                quantity=item_data['QuantityOrdered'],
                discount=promo_discount_subtotal,
                amazon_item_ref=amazon_item_ref,
                amazon_offer_id=offer.id,
            ))

            # Prepare the values for the gift wrap line.
            if item_data.get('IsGift', 'false') == 'true':
                item_gift_info = item_data.get('BuyerInfo', {})
                gift_wrap_code = item_gift_info.get('GiftWrapLevel')
                gift_wrap_price = float(item_gift_info.get('GiftWrapPrice', {}).get('Amount', '0'))
                if gift_wrap_code and gift_wrap_price != 0:
                    gift_wrap_product = self._find_matching_product(
                        gift_wrap_code, 'default_product', 'Amazon Sales', 'consu'
                    )
                    gift_wrap_product_taxes = gift_wrap_product.taxes_id.filtered_domain(
                        [*self.env['account.tax']._check_company_domain(self.company_id)]
                    )
                    gift_wrap_taxes = fiscal_pos.map_tax(gift_wrap_product_taxes) \
                        if fiscal_pos else gift_wrap_product_taxes
                    gift_wrap_tax_amount = float(
                        item_gift_info.get('GiftWrapTax', {}).get('Amount', '0')
                    )
                    original_gift_wrap_subtotal = gift_wrap_price - gift_wrap_tax_amount \
                        if marketplace.tax_included else gift_wrap_price
                    gift_wrap_subtotal = self._recompute_subtotal(
                        original_gift_wrap_subtotal,
                        gift_wrap_tax_amount,
                        gift_wrap_taxes,
                        currency,
                        fiscal_pos,
                    )
                    order_lines_values.append(convert_to_order_line_values(
                        product_id=gift_wrap_product.id,
                        description=_(
                            "[%s] Gift Wrapping Charges for %s",
                            gift_wrap_code, offer.product_id.name
                        ),
                        subtotal=gift_wrap_subtotal,
                        tax_ids=gift_wrap_taxes.ids,
                    ))
                gift_message = item_gift_info.get('GiftMessageText')
                if gift_message:
                    order_lines_values.append(convert_to_order_line_values(
                        description=_("Gift message:\n%s", gift_message),
                        display_type='line_note',
                    ))

            # Prepare the values for the delivery charges.
            shipping_code = order_data.get('ShipServiceLevel')
            if shipping_code:
                shipping_price = float(item_data.get('ShippingPrice', {}).get('Amount', '0'))
                shipping_product_taxes = shipping_product.taxes_id.filtered_domain(
                    [*self.env['account.tax']._check_company_domain(self.company_id)]
                )
                shipping_taxes = fiscal_pos.map_tax(shipping_product_taxes) if fiscal_pos \
                    else shipping_product_taxes
                shipping_tax_amount = float(item_data.get('ShippingTax', {}).get('Amount', '0'))
                origin_ship_subtotal = shipping_price - shipping_tax_amount \
                    if marketplace.tax_included else shipping_price
                shipping_subtotal = self._recompute_subtotal(
                    origin_ship_subtotal, shipping_tax_amount, shipping_taxes, currency, fiscal_pos
                )
                ship_discount = float(item_data.get('ShippingDiscount', {}).get('Amount', '0'))
                ship_disc_tax = float(item_data.get('ShippingDiscountTax', {}).get('Amount', '0'))
                origin_ship_disc_subtotal = ship_discount - ship_disc_tax \
                    if marketplace.tax_included else ship_discount
                ship_discount_subtotal = self._recompute_subtotal(
                    origin_ship_disc_subtotal, ship_disc_tax, shipping_taxes, currency, fiscal_pos
                )
                order_lines_values.append(convert_to_order_line_values(
                    product_id=shipping_product.id,
                    description=_(
                        "[%s] Delivery Charges for %s", shipping_code, offer.product_id.name
                    ),
                    subtotal=shipping_subtotal,
                    tax_ids=shipping_taxes.ids,
                    discount=ship_discount_subtotal,
                ))

        return order_lines_values

    def _find_or_create_offer(self, sku, marketplace):
        """ Find or create the amazon offer based on the SKU and marketplace.

        Note: self.ensure_one()

        :param str sku: The SKU of the product.
        :param recordset marketplace: The marketplace of the offer, as an `amazon.marketplace`
               record.
        :return: The amazon offer.
        :rtype: record or `amazon.offer`
        """
        self.ensure_one()

        offer = self.offer_ids.filtered(lambda o: o.sku == sku)
        if not offer:
            offer = self.env['amazon.offer'].with_context(tracking_disable=True).create({
                'account_id': self.id,
                'marketplace_id': marketplace.id,
                'product_id': self._find_matching_product(
                    sku, 'default_product', 'Amazon Sales', 'consu'
                ).id,
                'sku': sku,
            })
        # If the offer has been linked with the default product, search if another product has now
        # been assigned the current SKU as internal reference and update the offer if so.
        # This trades off a bit of performance in exchange for a more expected behavior for the
        # matching of products if one was assigned the right SKU after that the offer was created.
        elif 'sale_amazon.default_product' in offer.product_id._get_external_ids().get(
            offer.product_id.id, []
        ):
            product = self._find_matching_product(sku, '', '', '', fallback=False)
            if product:
                offer.product_id = product.id
        return offer

    def _find_or_create_pricelist(self, currency):
        """ Find or create the pricelist based on the currency.

        Note: self.ensure_one()

        :param recordset currency: The currency of the pricelist, as a `res.currency` record.
        :return: The pricelist.
        :rtype: record or `product.pricelist`
        """
        self.ensure_one()
        pricelist = self.env['product.pricelist'].with_context(active_test=False).search([
            *self.env['product.pricelist']._check_company_domain(self.company_id),
            ('currency_id', '=', currency.id),
        ], limit=1)
        if not pricelist:
            pricelist = self.env['product.pricelist'].with_context(tracking_disable=True).create({
                'name': 'Amazon Pricelist %s' % currency.name,
                'active': False,
                'currency_id': currency.id,
                'company_id': self.company_id.id,
            })
        return pricelist

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
        :rtype: record of `product.product`
        """
        self.ensure_one()
        product = self.env['product.product'].search([
            *self.env['product.product']._check_company_domain(self.company_id),
            ('default_code', '=', internal_reference),
        ], limit=1)
        if not product and fallback:  # Fallback to the default product
            product = self.env.ref('sale_amazon.%s' % default_xmlid, raise_if_not_found=False)
        if not product and fallback:  # Restore the default product if it was deleted
            product = self.env['product.product']._restore_data_product(
                default_name, default_type, default_xmlid
            )
        return product

    def _recompute_subtotal(self, subtotal, tax_amount, taxes, currency, _fiscal_pos=None):
        """ Recompute the subtotal from the tax amount and the taxes.

        As it is not always possible to find the right tax record for a tax rate computed from the
        tax amount because of rounding errors or because of multiple taxes for a given rate, the
        taxes on the product (or those given by the fiscal position) are used instead.

        To achieve this, the subtotal is recomputed from the taxes for the total to match that of
        the order in SellerCentral. If the taxes used are not identical to that used by Amazon, the
        recomputed subtotal will differ from the original subtotal.

        :param float subtotal: The original subtotal to use for the computation of the base total.
        :param float tax_amount: The original tax amount to use for the computation of the base
                                 total.
        :param recordset taxes: The final taxes to use for the computation of the new subtotal, as
                                an `account.tax` recordset.
        :param recordset currency: The currency used by the rounding methods, as a `res.currency`
                                   record.
        :param recordset _fiscal_pos: The fiscal position only used in overrides of this method, as
                                      an `account.fiscal.position` recordset.
        :return: The new subtotal.
        :rtype: float
        """
        total = subtotal + tax_amount
        taxes_res = taxes.with_context(force_price_include=True).compute_all(
            total, currency=currency
        )
        subtotal = taxes_res['total_excluded']
        for tax_res in taxes_res['taxes']:
            tax = self.env['account.tax'].browse(tax_res['id'])
            if tax.price_include:
                subtotal += tax_res['amount']
        return subtotal

    def _generate_stock_moves(self, order):
        """ Generate a stock move for each product of the provided sales order.

        :param recordset order: The sales order to generate the stock moves for, as a `sale.order`
                                record.
        :return: The generated stock moves.
        :rtype: recordset of `stock.move`
        """
        customers_location = self.env.ref('stock.stock_location_customers')
        for order_line in order.order_line.filtered(
            lambda l: l.product_id.type != 'service' and not l.display_type
        ):
            stock_move = self.env['stock.move'].create({
                'name': _('Amazon move: %s', order.name),
                'company_id': self.company_id.id,
                'product_id': order_line.product_id.id,
                'product_uom_qty': order_line.product_uom_qty,
                'product_uom': order_line.product_uom.id,
                'location_id': self.location_id.id,
                'location_dest_id': customers_location.id,
                'state': 'confirmed',
                'sale_line_id': order_line.id,
            })
            stock_move._set_quantity_done(order_line.product_uom_qty)
            stock_move.picked = True  # To also change move lines created in `_set_quantity_done`
            stock_move._action_done()

    def _sync_inventory(self):
        """ Synchronize the inventory availability of products sold on Amazon.

        If called on an empty recordset, the products of all active accounts with inventory
        synchronization are synchronized instead.

        Note: This method is called by the `ir_cron_sync_amazon_inventory` cron.

        :return: None
        """
        self = self or self.search([])
        accounts = self.filtered('synchronize_inventory')
        if not accounts:
            return

        # Cache `free_qty` of all products to avoid recomputing it for each offer.
        accounts.offer_ids.product_id.filtered(lambda p: p.type == 'product')._compute_quantities()

        for account in accounts:
            amazon_utils.ensure_account_is_set_up(account)
            offers = account.offer_ids.filtered(lambda o: o.product_id.type == 'product')
            offers._update_inventory_availability(account)

        # As Amazon needs some time to process the feed, we trigger the cron to check the status of
        # the feed after 10 minutes.
        next_call = fields.Datetime.now() + timedelta(minutes=10)
        self.env.ref('sale_amazon.ir_cron_sync_amazon_feeds')._trigger(at=next_call)

    def _sync_feeds(self):
        """ Synchronize the status of the accounts' feeds that were sent to Amazon.

        If called on an empty recordset, the feeds of all active account are synchronized instead.

        We assume that the combined set of feeds (of all accounts) to be handled will always be too
        small for the cron to be killed before it finishes synchronizing all feeds.

        Note: This method is called by the `ir_cron_sync_amazon_feeds` cron.

        :return: None
        """
        self = self or self.search([])

        # Select accounts with offers or pickings requiring synchronization.
        accounts_with_offers = self.filtered(
            lambda a: any(o.amazon_sync_status == 'processing' for o in a.offer_ids)
        )
        pickings_by_account = self.env['stock.picking']._get_pickings_by_account(
            'processing', tuple(self.ids)
        )

        # Syn feeds status.
        for account in accounts_with_offers:
            amazon_utils.ensure_account_is_set_up(account)
            offers = account.offer_ids.filtered(lambda o: o.amazon_sync_status == 'processing')
            account._pull_feeds_status(offers, 'inventory_sync')
        for account, pickings in pickings_by_account.items():
            amazon_utils.ensure_account_is_set_up(account)
            account._pull_feeds_status(pickings, 'picking_sync')

        # Re-schedule the cron if not all the offers and pickings reached a final status.
        any_processing_feed = any(
            offer.amazon_sync_status == 'processing' for offer in accounts_with_offers.offer_ids
        ) or any(
            account_pickings.filtered(lambda p: p.amazon_sync_status == 'processing')
            for account_pickings in pickings_by_account.values()
        )
        if any_processing_feed:
            next_call = fields.Datetime.now() + timedelta(minutes=10)
            self.env.ref('sale_amazon.ir_cron_sync_amazon_feeds')._trigger(at=next_call)

    def _pull_feeds_status(self, records, flow):
        """ Pull the status of the feeds corresponding to the provided recordset.

        Note: `self.ensure_one()`

        :param recordset records: The records whose feed status should be pulled. Only
                                  `amazon.offer` and `stock.picking` are supported.
        :param str flow: The feed name that must be fetched. Supported feeds are 'inventory_sync'
                         and 'picking_sync'.
        :return: None
        """
        self.ensure_one()

        if flow == 'inventory_sync':
            record_model = self.env['amazon.offer']
        elif flow == 'picking_sync':
            record_model = self.env['stock.picking']
        else:
            return

        records_by_feed = {}
        for record in records:
            records_by_feed.setdefault(record.amazon_feed_ref, record_model)
            records_by_feed[record.amazon_feed_ref] += record

        errors_by_record = {}
        for feed_ref, feed_records in records_by_feed.items():
            # Pull the status and result document reference for the current feed.
            feed_data = amazon_utils.make_sp_api_request(self, 'getFeed', path_parameter=feed_ref)
            feed_status = feed_data['processingStatus']
            result_document_ref = feed_data.get('resultFeedDocumentId')

            # Update the records according to their feed status.
            if feed_status == 'DONE':  # The feed was fully processed.
                try:
                    document = amazon_utils.get_feed_document(self, result_document_ref)
                except amazon_utils.AmazonRateLimitError:
                    raise  # Don't treat a rate limit error as a business error.
                except ValidationError:
                    _logger.exception(
                        "A business error occurred while processing feed %(feed_ref)s for Amazon"
                        " account with id %(account_id)s. Skipping the feed and moving to the next"
                        " one.", {'feed_ref': feed_ref, 'account_id': self.id}
                    )
                else:
                    if document.find('ProcessingSummary/MessagesWithError').text == '0':
                        feed_records.amazon_sync_status = 'done'
                        _logger.info(
                            "Synchronized feed %(feed_ref)s for Amazon account with id"
                            " %(account_id)s.", {'feed_ref': feed_ref, 'account_id': self.id}
                        )
                        continue

                    # Iterate over the processing results and flag failed records as in 'error'.
                    consider_unprocessed_records_as_failed = False
                    for result_message in document.iter('Result'):
                        result_code = result_message.find('ResultCode').text
                        if result_code != 'Error':
                            continue
                        if flow == 'inventory_sync':
                            sku = result_message.find('AdditionalInfo/SKU').text
                            failed_offer = feed_records.filtered(lambda o: o.sku == sku)
                            # Using a set to combine duplicates created by Amazon with every retry.
                            errors_by_record.setdefault(failed_offer, set())
                            errors_by_record[failed_offer].add(
                                result_message.find('ResultDescription').text
                            )
                        elif flow == 'picking_sync':
                            order_info = result_message.find('AdditionalInfo/AmazonOrderID')
                            order_id = order_info is not None and order_info.text
                            if order_id:  # We can identify failed pickings.
                                error_desc = result_message.find('ResultDescription').text
                                failed_pickings = feed_records.filtered(
                                    lambda p: p.sale_id.amazon_order_ref == order_id
                                )
                                for failed_picking in failed_pickings:
                                    errors_by_record.setdefault(failed_picking, set())
                                    errors_by_record[failed_picking].add(error_desc)
                            else:  # Amazon doesn't specify which order (and thus picking) failed.
                                consider_unprocessed_records_as_failed = True
                    feed_records.filtered(
                        lambda p: p in errors_by_record
                    ).amazon_sync_status = 'error'
                    unprocessed_records = feed_records.filtered(
                        lambda p: p.amazon_sync_status == 'processing'
                    )  # The sync order might have run before, avoid changing back done records.
                    if consider_unprocessed_records_as_failed:
                        for record in unprocessed_records:
                            errors_by_record.setdefault(record, set()).add(None)
                        unprocessed_records.amazon_sync_status = 'error'
                    else:  # All errors were identified, the remaining records succeeded.
                        unprocessed_records.amazon_sync_status = 'done'
                    _logger.info(
                        "Found errors while synchronizing feed %(feed_ref)s for Amazon account with"
                        " id %(account_id)s.", {'feed_ref': feed_ref, 'account_id': self.id}
                    )

            elif feed_status in ['IN_QUEUE', 'IN_PROGRESS']:  # The feed has not yet been processed.
                _logger.info(
                    "Ignoring in progress feed %(feed_ref)s for Amazon account with id"
                    " %(account_id)s.", {'feed_ref': feed_ref, 'account_id': self.id}
                )

            elif feed_status == 'CANCELLED':  # The feed has been canceled before being processed.
                feed_records.amazon_sync_status = 'pending'
                if flow == 'inventory_sync':
                    _logger.info(
                        "Re-scheduling a synchronization of inventory for offers of canceled"
                        " feed %(feed_ref)s for Amazon account with id %(account_id)s.",
                        {'feed_ref': feed_ref, 'account_id': self.id},
                    )
                elif flow == 'picking_sync':
                    _logger.info(
                        "Re-scheduling a synchronization for pickings of canceled feed %(feed_ref)s"
                        " for Amazon account with id %(account_id)s.",
                        {'feed_ref': feed_ref, 'account_id': self.id},
                    )

            elif feed_status == 'FATAL':  # The feed failed with no further information.
                for record in feed_records:
                    errors_by_record.setdefault(record, set()).add(None)
                feed_records.amazon_sync_status = 'error'

        if errors_by_record:
            error_messages = []
            for r, errors in errors_by_record.items():
                for error in errors:
                    if error and flow == 'picking_sync':
                        r.message_post(body=Markup("%s<br/>%s") % (
                            _("The synchronization with Amazon failed. Amazon gave us this "
                              "information about the problem:"),
                            error,
                        ))
                    if flow == 'inventory_sync':
                        error_messages.append({'sku': r.sku, 'message': error})
                    elif flow == 'picking_sync':
                        error_messages.append(
                            {'order_ref': r.sale_id.amazon_order_ref, 'message': error}
                        )

            self._handle_sync_failure(flow=flow, error_messages=error_messages)

    def _handle_sync_failure(self, flow, amazon_order_ref=False, error_messages=False):
        """ Send a mail to the responsible persons to report a synchronization failure.

        :param str flow: The flow for which the failure mail is requested. Supported flows are:
                        `order_sync`, `inventory_sync`, and `picking_sync`.
        :param str amazon_order_ref: The amazon reference of the order that failed to synchronize.
                                     Required for the `order_sync` flow.
        :param list[dict] error_messages: A list containing the referenced Amazon orders and their
                                           linked errors in the format [{'order_ref': 'error'}].
                                           Required for the `picking_sync` flow.
        :return: None
        """
        if flow == 'order_sync':
            _logger.exception(
                "Failed to synchronize order with amazon reference %(ref)s for amazon.account with "
                "id %(account_id)s (seller id %(seller_id)s).",
                {'ref': amazon_order_ref, 'account_id': self.id, 'seller_id': self.seller_key},
            )
            mail_template_id = 'sale_amazon.order_sync_failure'
        elif flow == 'inventory_sync':
            _logger.exception(
                "Failed to synchronize the inventory for offers in amazon.account with id "
                "%(account_id)s (seller id %(seller_id)s).",
                {'account_id': self.id, 'seller_id': self.seller_key}
            )
            mail_template_id = 'sale_amazon.inventory_sync_failure'
        else:  # flow == 'picking_sync':
            _logger.exception(
                "Failed to synchronize pickings for amazon.account with id %(account_id)s "
                "(seller id %(seller_id)s).", {'account_id': self.id, 'seller_id': self.seller_key}
            )
            mail_template_id = 'sale_amazon.picking_sync_failure'

        mail_template = self.env.ref(mail_template_id, raise_if_not_found=False)
        if not mail_template:
            _logger.warning("The mail template with xmlid %s has been deleted.", mail_template_id)
        else:
            responsible_emails = {user.email for user in filter(
                None, (self.user_id, self.env.ref('base.user_admin', raise_if_not_found=False))
            )}
            mail_template.with_context(**{
                'email_to': ','.join(responsible_emails),
                'amazon_order_ref': amazon_order_ref,
                'error_messages': error_messages,
                'amazon_account': self.name,
            }).send_mail(self.env.user.id)
            _logger.info(
                "Sent synchronization failure notification email to %s",
                ', '.join(responsible_emails)
            )
