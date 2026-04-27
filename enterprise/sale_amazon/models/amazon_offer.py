# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import api, fields, models
from odoo.tools import split_every

from odoo.addons.sale_amazon import utils as amazon_utils


_logger = logging.getLogger(__name__)


class AmazonOffer(models.Model):
    _name = 'amazon.offer'
    _description = "Amazon Offer"

    def _default_marketplace(self):
        """ Return the single marketplace of this offer's account if it exists. """
        account_id = self.env.context.get('default_account_id')
        if account_id:
            marketplaces = self.env['amazon.account'].browse([account_id]).active_marketplace_ids
            return len(marketplaces) == 1 and marketplaces[0]

    account_id = fields.Many2one(
        string="Account",
        help="The seller account used to manage this product.",
        comodel_name='amazon.account',
        required=True,
        ondelete='cascade',
    )  # The default account provided in the context of the list view.
    company_id = fields.Many2one(related='account_id.company_id', readonly=True)
    active_marketplace_ids = fields.Many2many(related='account_id.active_marketplace_ids')
    marketplace_id = fields.Many2one(
        string="Marketplace",
        help="The marketplace of this offer.",
        comodel_name='amazon.marketplace',
        default=_default_marketplace,
        required=True,
        domain="[('id', 'in', active_marketplace_ids)]",
    )
    product_id = fields.Many2one(
        string="Product", comodel_name='product.product', required=True, ondelete='cascade'
    )
    product_template_id = fields.Many2one(
        related="product_id.product_tmpl_id", store=True, readonly=True
    )
    sku = fields.Char(string="SKU", help="The Stock Keeping Unit.", required=True)
    amazon_sync_status = fields.Selection(
        string="Amazon Synchronization Status",
        help="The synchronization status of the product's stock level to Amazon:\n"
             "- Processing: The stock level has been sent and is being processed.\n"
             "- Done: The stock level has been processed.\n"
             "- Error: The synchronization of the stock level failed.",
        selection=[('processing', "Processing"), ('done', "Done"), ('error', "Error")],
        readonly=True,
    )
    amazon_feed_ref = fields.Char(string="Amazon Feed Reference", readonly=True)

    _sql_constraints = [(
        'unique_sku', 'UNIQUE(account_id, sku)', "SKU must be unique for a given account."
    )]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Set the SKU to the internal reference of the product if it exists. """
        for offer in self:
            offer.sku = offer.product_id.default_code

    def action_view_online(self):
        self.ensure_one()
        url = f'{self.marketplace_id.seller_central_url}/skucentral?mSku={self.sku}'
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def _get_feed_data(self):
        """Load the necessary data for the inventory feed, and fetch the missing ones.

        :return: A dictionary per offer in `self`.
            Each dictionnary contains at least the `productType` and a flag `is_fbm`.
            If any of these attributes is missing and fails to be fetch (rate limit), the data for
            the offer are not returned.
        :rtype: dict[amazon.offer, dict]
        """
        feed_data_by_offer = {}
        for offer in self:
            try:
                feed_data = json.loads(offer.amazon_feed_ref)
            except (json.JSONDecodeError, TypeError):  # field is either incorrect JSON, or False
                feed_data = None
            if isinstance(feed_data, dict):  # In case old `amazon_feed_ref` are still stored
                feed_data_by_offer[offer] = feed_data

        if self.env.context.get("amzn_fetch_missing_data", True) and (
            offers_with_missing_data := self.filtered(
                lambda offer_: (
                    not (
                        offer_ in feed_data_by_offer
                        and "productType" in feed_data_by_offer[offer_]
                        and "is_fbm" in feed_data_by_offer[offer_]
                    )
                )
            )
        ):
            feed_data_by_offer.update(
                offers_with_missing_data._fetch_and_save_feed_data()  # fetch missing data
            )

        return feed_data_by_offer

    def _fetch_and_save_feed_data(self):
        """Fetch data necessary for the inventory feed to work and save it in the record.

        Necessary data are:
            - productType: Amazon product type
            - is_fbm: is fulfilled by merchant

        :return: A mapping of offer to feed data
        :rtype: dict['amazon.offer', dict]
        """
        feed_data_by_offer = {}
        to_fetch = self.sorted(lambda o:
            o.amazon_sync_status != 'error'  # previously failed fetch first (rate limit)
        ).grouped(lambda o: (o.account_id, o.marketplace_id))
        # searchListingsItems only supports up to 20 SKUs
        to_fetch = (
            (group, batch)
            for group, offers in to_fetch.items()
            for batch in split_every(20, offers.ids, self.env['amazon.offer'].browse)
        )
        for (account_id, marketplace_id), offers in to_fetch:
            try:
                response = amazon_utils.make_sp_api_request(
                    account=account_id,
                    operation='searchListingsItems',
                    path_parameter=account_id.seller_key,
                    payload={
                        'marketplaceIds': marketplace_id.api_ref,
                        'includedData': 'attributes,productTypes',
                        'identifiersType': 'SKU',
                        'identifiers': ','.join(offer.sku.replace(',', '') for offer in offers),
                        'pageSize': len(offers),
                    },
                )
            except amazon_utils.AmazonRateLimitError:
                _logger.warning("Could not fetch every offers infos due to rate limit from Amazon.")
                # Mark failed offers, to be prioritized on next try
                offers.amazon_sync_status = 'error'
                continue

            # Parse product data
            offer_by_sku = offers.grouped('sku')
            feed_data_by_offer.update(
                {offer: {'productType': False, 'is_fbm': False} for offer in offers}
            )  # Default to FBA to not fetch the info everytime when the offer isn't found by Amazon
            for item in response['items']:
                feed_data_by_offer[offer_by_sku[item['sku']]] = {
                    'productType':
                        item['productTypes'] and item['productTypes'][0]['productType']
                        or 'PRODUCT',
                    'is_fbm': 'merchant_shipping_group' in item['attributes'],
                }

        # Save data to reduce api calls
        AmazonOffer._save_feed_data(feed_data_by_offer)

        return feed_data_by_offer

    @classmethod
    def _save_feed_data(cls, feed_data_by_offer):
        """Save inventory feed data.

        :param dict['amazon.offer', dict] feed_data_by_offer: A mapping from offer to data necessary
            for the inventory feed.
        """
        for offer, feed_info in feed_data_by_offer.items():
            offer.amazon_feed_ref = json.dumps(feed_info, separators=(',', ':'))

    def _update_inventory_availability(self, account):
        """Update the stock quantity of Amazon products to Amazon.

        Note: only synchronizes the stock of FBM offers.

        :param record account: The Amazon account on behalf of which the feed should be
            built and submitted.
        :return: None
        """

        feed_data_by_offer = self._get_feed_data()
        # Filter offers missing feed data and synchronize FBM offers only
        self = self.filtered(lambda o: o in feed_data_by_offer and feed_data_by_offer[o]['is_fbm'])

        # Inventory feed can only apply to one marketplace
        for marketplace_id, offers in self.grouped('marketplace_id').items():
            offers._send_inventory_feed(
                account,
                {o: feed_data_by_offer[o] for o in offers},
                marketplace_id,
            )

    def _send_inventory_feed(self, account, feed_data_by_offer, marketplace_id):
        """Send the inventory feed for the given marketplace.

        Note: A feed of type `JSON_LISTINGS_FEED` can be applied to only one marketplace.

        :param 'amazon.account' account: The Amazon account on behalf of which the feed should be
            built and submitted.
        :param dict['amazon.offer', dict] feed_data_by_offer: A mapping of offer to their feed data,
            i.e. at least the 'productType' of the offer.
        :param 'amazon.marketplace' marketplace_id: The marketplace to which the feed should apply.
        """
        for i, feed_info in enumerate(feed_data_by_offer.values(), start=1):
            # Assign and save the message id to later match error message(s)
            feed_info['messageId'] = i
        messages = self._build_feed_messages(feed_data_by_offer)
        json_feed = amazon_utils.build_json_feed(account, messages)
        try:
            feed_ref = amazon_utils.submit_feed(
                account,
                json_feed,
                'JSON_LISTINGS_FEED',
                feed_content_type='application/json; charset=UTF-8',
                marketplace_api_refs=[marketplace_id.api_ref],
            )
        except amazon_utils.AmazonRateLimitError:
            _logger.info(
                "Rate limit reached while sending inventory availability notification for Amazon"
                " account with id %s.", account.id
            )
        else:
            _logger.info(
                "Sent inventory availability notification (feed_ref %s) to Amazon for account ID"
                " %s. SKUs: %s.",
                feed_ref,
                account.id,
                ', '.join(self.mapped('sku')),
            )
            self.amazon_sync_status = 'processing'
            # Save feed reference to later sync any error that might have occurred
            for feed_info in feed_data_by_offer.values():
                feed_info['amazon_feed_ref'] = feed_ref
            # Save message IDs
            self._save_feed_data(feed_data_by_offer)

    def _build_feed_messages(self, feed_data_by_offer):
        """Constructs the inventory feed messages.

        :param dict['amazon.offer', dict] feed_data_by_offer: A dict mapping offer with the
            necessary feed data, i.e. productType and messageId.
        :rtype: list[dict]
        """
        return [
            {
                'messageId': feed_data['messageId'],
                'sku': offer.sku,
                'operationType': 'PARTIAL_UPDATE',
                'productType': feed_data['productType'],
                'attributes': {
                    'fulfillment_availability': [{
                        'fulfillment_channel_code': 'DEFAULT',
                        'quantity':
                            (qty := int(offer._get_available_product_qty())) > 0 and qty or 0,
                    }]
                }
            }
            for offer, feed_data in feed_data_by_offer.items()
        ]

    def _get_available_product_qty(self):
        """ Retrieve the current available and free product quantity.

        This hook can be overridden to set a finer quantity.

        :return: The free quantity.
        :rtype: float
        """
        self.ensure_one()
        return self.product_id.free_qty
