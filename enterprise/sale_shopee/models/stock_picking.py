# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import  _, fields, models

from odoo.addons.sale_shopee import const, utils

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shopee_order_ref = fields.Char(related='sale_id.shopee_order_ref')
    shopee_delivery_status = fields.Selection(related='sale_id.shopee_delivery_status')
    shopee_label_status = fields.Selection(
        string="Label Status",
        help="The status of the shipping label:\n"
             "- Not Available: The shipping label is not available yet.\n"
             "- Processing: The shipping label is being processed.\n"
             "- Ready: The shipping label is ready to be downloaded.\n"
             "- Stored: The shipping label has been downloaded and stored.\n"
             "- Failed: The shipping label creation failed.",
        selection=[
            ('not available', "Not Available"),
            ('processing', "Processing"),
            ('ready', "Ready"),
            ('stored', "Stored"),
            ('failed', "Failed"),
        ],
        readonly=True,
        default='not available',
    )
    last_picking_sync_date = fields.Datetime(
        help="The last time the picking was synchronized with Shopee.",
        readonly=True,
        default=fields.Datetime.now,
    )

    # === ACTION METHODS === #

    def action_shopee_sync_pickings(self):
        return self._sync_shopee_pickings()

    # === BUSINESS METHODS === #

    def _sync_shopee_pickings(self, shop_ids=(), auto_commit=True):
        """ Fetch tracking number and shipping label from Shopee.

        Delivery information needs to be filled directly on Shopee, once done, Shopee will assign a
        tracking number to the pickings. _sync_picking will fetch this number, and create the
        associated shipping label.

        :param tuple shop_ids: The shop whose deliveries should be synchronized, as a tuple of
                               `shopee.shop` record ids.
        :param auto_commit: If True, the transaction will be committed after each successful sync
        :return: None
        """
        pickings_by_shop = self._get_pickings_by_shop(shop_ids)

        for shop, shop_pickings in pickings_by_shop.items():
            try:
                shop._update_shop_information()
                if shop.status != 'active':
                    continue
                shop_pickings._fetch_shipment_label(auto_commit)
            except utils.ShopeeRateLimitError as error:
                _logger.info(
                    "Rate limit reached while synchronizing pickings for Shopee account with"
                    " id %(account)d. Operation: %(error_operation)s",
                    {'account': shop.account_id.id, 'error_operation': error.operation},
                )
                continue

        # If there are pickings in processing status, schedule a cron to retry in 1 minute
        all_pickings = self.env['stock.picking'].concat(*pickings_by_shop.values())
        processing_pickings = all_pickings.filtered(lambda p: p.shopee_label_status == 'processing')
        if processing_pickings:
            cron = self.env.ref('sale_shopee.ir_cron_sync_shopee_pickings_retry')
            cron._trigger(at=fields.Datetime.now() + timedelta(minutes=1))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Shipping Label Not Ready"),
                    'message': _(
                        "Shopee is processing the shipping label. Odoo will try fetching the"
                        " shipping label again later."
                    ),
                    'type': 'warning',
                },
            }

    def _get_pickings_by_shop(self, shop_ids=()):
        """ Group the pickings by their respective shops.

        :param tuple shop_ids: The shops whose pickings should be considered, as a tuple of
                              `shopee.shop` records ids.
        :return: The pickings grouped by Shopee shop.
        :rtype: dict
        """
        pickings_by_shop = {}
        domain = [
            ('sale_id.shopee_shop_id', '!=', False),
            ('shopee_order_ref', '!=', False),
            ('shopee_delivery_status', 'in', ['draft', 'confirmed']),
            ('shopee_label_status', '!=', 'stored'),
            ('state', 'not in', ['done', 'cancel']),
        ]
        if self:
            domain.append(['id', 'in', self.ids])
        if shop_ids:
            domain.append(('sale_id.shopee_shop_id', 'in', shop_ids))

        for picking in self.search(domain):

            shop = picking.sale_id.shopee_shop_id
            if not shop:
                continue
            pickings_by_shop.setdefault(shop, self.env['stock.picking'])
            pickings_by_shop[shop] += picking

        return pickings_by_shop

    def _fetch_shipment_label(self, auto_commit=True):
        """ Fetch tracking number and shipping label from Shopee.

        Delivery information needs to be filled directly on Shopee, once done, Shopee will assign a
        tracking number to the pickings. _sync_picking will fetch this number, and create the
        associated shipping label.

        :param auto_commit: If True, the transaction will be committed after each successful sync
        :return: None
        """
        shop = self[0].sale_id.shopee_shop_id
        shop.ensure_one()

        # fetch tracking numbers for pickings without tracking number
        # fetch pickings 50 per 50 and sort by the last_shopee_sync_date to avoid cron timeout
        error_messages = []
        current_datetime = fields.Datetime.now()
        picking_sorted = self.filtered(
            lambda p: p.state not in ['cancel', 'done'] \
            and p.shopee_label_status != 'stored' \
            and p.shopee_delivery_status in ['draft', 'confirmed']
        ).sorted(lambda p: (p.last_picking_sync_date, p.id))

        batch_size = min(const.ORDER_DETAIL_SIZE_LIMIT, const.SHIPPING_DOCUMENT_SIZE_LIMIT)  # same
        picking_batches = [
            picking_sorted[i:i + batch_size] for i in range(0, len(picking_sorted), batch_size)
        ]
        for picking_batch in picking_batches:
            try:
                # Update the order delivery status in case it changed.
                orders_detail = shop._fetch_orders_detail(picking_batch.sale_id.mapped('shopee_order_ref'))
                for order_detail in orders_detail:
                    new_delivery_status = const.DELIVERY_STATUS_MAPPING.get(
                        order_detail['order_status'], 'error'
                    )
                    order = picking_batch.sale_id.filtered(
                        lambda o: o.shopee_order_ref == order_detail['order_sn']
                    )
                    if order and order.shopee_delivery_status != new_delivery_status:
                        order.shopee_delivery_status = new_delivery_status

                picking_batch = picking_batch.filtered(
                    lambda p: p.shopee_delivery_status in {'draft', 'confirmed'}
                )

                # Set the tracking number as soon as it's available
                picking_batch._set_tracking_number(shop)
                pickings = picking_batch.filtered(lambda p: p.carrier_tracking_ref)

                # Request shipping label
                pickings_no_label_requested = pickings.filtered(
                    lambda p: p.shopee_label_status in ['not available', 'failed']
                )
                pickings_no_label_requested._generate_shipping_label(shop)

                # Fetch the shipping label status to flag the pickings ready to be downloaded.
                pickings_label_requested = pickings.filtered(
                    lambda p: p.shopee_label_status == 'processing'
                )
                pickings_label_requested._fetch_shipping_label_status(shop)

                # Download the shipping label
                pickings_label_ready_to_print = pickings.filtered(
                    lambda p: p.shopee_label_status == 'ready'
                )
                pickings_label_ready_to_print._download_shipping_label(shop)
            except utils.ShopeeRateLimitError:
                raise
            except Exception as error:
                error_messages.append({
                    'batch_picking_refs': ", ".join(picking_batch.mapped('name')),
                    'message': str(error),
                })
                continue
            finally:
                picking_batch.write({'last_picking_sync_date': current_datetime})
                if auto_commit:
                    self.env.cr.commit()

        if error_messages:
            shop._handle_sync_failure(flow='picking_sync', error_messages=error_messages)

    def _set_tracking_number(self, shop):
        """ Fetch the tracking number from Shopee API and update the carrier_tracking_ref field.

        If the tracking number is not available, the field will be left empty.

        :param record shop: The Shopee shop of the pickings as a `shopee.shop` record.
        :return: None
        """
        for picking in self.filtered(lambda p: not p.carrier_tracking_ref):
            tracking_number = utils.make_shopee_api_request(
                shop, 'get_tracking_number', {'order_sn': picking.shopee_order_ref}
            ).get('tracking_number')
            if tracking_number:
                picking.carrier_tracking_ref = tracking_number

    def _generate_shipping_label(self, shop):
        """ Initiate the shipping label generation from Shopee for the pickings.

        :param record shop: The Shopee shop of the pickings as a `shopee.shop` record.
        :return: None
        """

        for i in range(0, len(self), const.SHIPPING_DOCUMENT_SIZE_LIMIT):
            pickings = self[i:i + const.SHIPPING_DOCUMENT_SIZE_LIMIT]
            order_list = [{
                'order_sn': pick.shopee_order_ref, 'tracking_number': pick.carrier_tracking_ref,
            } for pick in pickings]
            response = utils.make_shopee_api_request(
                shop, 'create_shipping_document', body={'order_list': order_list}, method='POST'
            )
            failed_orders = {
                result['order_sn'] for result in response['result_list'] if result.get('fail_error')
            }

            failed_pickings = pickings.filtered(lambda p: p.shopee_order_ref in failed_orders)
            failed_pickings.shopee_label_status = 'failed'

            successful_pickings = pickings - failed_pickings
            successful_pickings.shopee_label_status = 'processing'

    def _fetch_shipping_label_status(self, shop):
        """ Fetch the shipping label from Shopee API and update the label status for the pickings.

        :param record shop: The Shopee shop of the pickings as a `shopee.shop` record.
        :return: None
        """
        for i in range(0, len(self), const.SHIPPING_DOCUMENT_SIZE_LIMIT):
            pickings = self[i:i + const.SHIPPING_DOCUMENT_SIZE_LIMIT]
            order_list = [{'order_sn': picking.shopee_order_ref} for picking in pickings]
            response = utils.make_shopee_api_request(
                shop, 'get_shipping_document_result', body={'order_list': order_list}, method='POST'
            )
            order_sn_status = {res['order_sn']: res['status'] for res in response['result_list']}
            for picking in pickings:  # update the label status for each picking
                status = order_sn_status.get(picking.shopee_order_ref)
                if status:
                    picking.shopee_label_status = const.LOWER_SHIPPING_LABEL_MAPPING.get(
                        status, 'failed'
                    )

    def _download_shipping_label(self, shop):
        """ Download the shipping labels and store them in the picking messages.

        :param record shop: The Shopee shop of the pickings as a `shopee.shop` record.
        :return: None
        """
        for picking in self:
            order_sn = picking.shopee_order_ref
            content = utils.make_shopee_api_request(shop, 'download_shipping_document', body={
                'order_list': [{'order_sn': order_sn}],
            }, method='POST')
            # If the label exists in the picking messages, do not store it again
            attachment_name = f"Shopee_Label_{picking.name.replace(' ', '_')}.pdf"
            existing_attachment = self.env['ir.attachment'].search([
                ('company_id', '=', self.company_id.id),
                ('name', '=', attachment_name),
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking.id),
            ], limit=1)
            if not existing_attachment:
                picking.message_post(
                    subject=_("Shopee Label"), attachments=[(attachment_name, content)]
                )
            picking.shopee_label_status = 'stored'

    def _sync_processing_pickings(self):
        """ Retry fetching shipping label from Shopee for pickings in processing status. """
        processing_pickings = self.search([('shopee_label_status', '=', 'processing')])
        if processing_pickings:
            return processing_pickings._sync_shopee_pickings()
