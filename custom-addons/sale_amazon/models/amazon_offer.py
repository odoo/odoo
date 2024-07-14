# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from xml.etree import ElementTree

from odoo import api, fields, models

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

    def _update_inventory_availability(self, account):
        """
        Update the stock quantity of Amazon products to Amazon.

        :param record account: The Amazon account of the delivery to confirm on Amazon, as an
                               `amazon.account` record.
        :return: None
        """

        def build_feed_messages(root_):
            """ Build the 'Message' elements to add to the feed.

            :param Element root_: The root XML element to which messages should be added.
            :return: None
            """
            location_ = self.account_id.location_id
            quant_ids_ = location_.quant_ids.filtered(lambda q: q.product_id in self.product_id)
            fba_offers_ = self.filtered(lambda o: o.product_id in quant_ids_.product_id)
            for offer_ in self:
                # Build the message base.
                message_ = ElementTree.SubElement(root_, 'Message')
                inventory_ = ElementTree.SubElement(message_, 'Inventory')
                ElementTree.SubElement(inventory_, 'SKU').text = offer_.sku
                # We consider products in the Amazon location to be FBA. Their quantity is set to 0
                # as we don't add any fulfillment channel to the feed. Amazon won't  change their
                # quantity on hand, but by forcing the quantity here, we make sure Amazon will not
                # consider we are selling it through another channel.
                free_qty_ = offer_.product_id.free_qty
                quantity_ = free_qty_ if offer_ not in fba_offers_ and free_qty_ > 0 else 0
                ElementTree.SubElement(inventory_, 'Quantity').text = str(int(quantity_))

        xml_feed = amazon_utils.build_feed(account, 'Inventory', build_feed_messages)
        try:
            feed_ref = amazon_utils.submit_feed(
                account, xml_feed, 'POST_INVENTORY_AVAILABILITY_DATA'
            )
        except amazon_utils.AmazonRateLimitError:
            _logger.info(
                "Rate limit reached while sending inventory availability notification for Amazon"
                " account with id %s.", account.id
            )
        else:
            _logger.info(
                "Sent inventory availability notification (feed_ref %s) to amazon for offers with"
                " SKU %s.",
                feed_ref,
                ', '.join(self.mapped('sku')),
            )
            self.write({'amazon_sync_status': 'processing', 'amazon_feed_ref': feed_ref})
