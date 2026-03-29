# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    bictorys_order_id = fields.Char(
        string="Bictorys Order ID",
        readonly=True,
        copy=False,
    )
    bictorys_payment_status = fields.Selection(
        selection=[
            ('pending', "Pending"),
            ('succeeded', "Succeeded"),
            ('failed', "Failed"),
        ],
        string="Bictorys Payment Status",
        readonly=True,
        copy=False,
    )

    @api.model
    def sync_from_ui(self, orders):
        """Override: after saving POS orders, create Bictorys orders.

        Exact same pattern as the original working module — search pos.payment
        by xmlid after super() call, then POST to Bictorys API.
        """
        pos_orders = super().sync_from_ui(orders)
        order_ids = [o['id'] for o in pos_orders.get('pos.order', [])]

        # Resolve the Bictorys POS payment method by xmlid.
        # This is the method created manually by the admin with use_payment_terminal='bictorys'.
        bictorys_pm = self.env.ref(
            'payment_bictorys.pos_payment_method_bictorys', raise_if_not_found=False
        )
        if not bictorys_pm:
            # Fallback: find any method with use_payment_terminal='bictorys'
            bictorys_pm = self.env['pos.payment.method'].sudo().search(
                [('use_payment_terminal', '=', 'bictorys')], limit=1
            )

        if not bictorys_pm:
            _logger.warning(
                "Bictorys: sync_from_ui — no Bictorys POS payment method found, skipping."
            )
            return pos_orders

        for order in self.browse(order_ids):
            _logger.info(
                "Bictorys: sync_from_ui — order id=%s name=%s state=%s",
                order.id, order.name, order.state,
            )
            # Find pos.payment lines for this order using the Bictorys method.
            payment_lines = self.env['pos.payment'].search([
                ('pos_order_id', '=', order.id),
                ('payment_method_id', '=', bictorys_pm.id),
            ])
            _logger.info(
                "Bictorys: order %s — bictorys payment lines: %s",
                order.name, len(payment_lines),
            )
            if payment_lines and not order.bictorys_order_id:
                order._bictorys_create_order(payment_lines)

        return pos_orders

    def _bictorys_create_order(self, payment_lines):
        """Create the order on the Bictorys platform."""
        self.ensure_one()

        provider = self.env['payment.provider'].sudo().search(
            [('code', '=', 'bictorys'), ('state', '!=', 'disabled')], limit=1
        )
        if not provider:
            _logger.warning("Bictorys: _bictorys_create_order — no active provider found.")
            return

        api_base = (
            'https://api.test.bictorys.com'
            if provider.state == 'test'
            else 'https://api.bictorys.com'
        )
        secret_key = provider.sudo().bictorys_secret_key
        if not secret_key:
            _logger.warning("Bictorys: _bictorys_create_order — no secret key configured.")
            return

        headers = {
            "accept": "application/problem+json",
            "content-type": "application/json",
            "X-API-Key": secret_key,
        }

        for pay in payment_lines:
            payload = {
                'reference': self.pos_reference,
                'amount': pay.amount,
                'currency': self.currency_id.name,
                'orderDetails': [
                    {
                        'name': line.full_product_name,
                        'reference': line.product_id.default_code or '',
                        'price': line.price_unit,
                        'quantity': line.qty,
                    }
                    for line in self.lines
                ],
                'deviceId': self.config_id.name,
                'status': 'opened',
            }

            url = f"{api_base}/order-management/v1/orders"
            _logger.info(
                "Bictorys: creating order for POS order %s:\n%s",
                self.name, pprint.pformat(payload),
            )
            _logger.info("================================ %s",url)

            retry = 0
            while retry < 2:
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    _logger.info(
                        "Bictorys: order creation response HTTP=%s body=%s",
                        response.status_code, response.text,
                    )
                    if response.status_code == 201:
                        data = response.json()
                        self.write({
                            'bictorys_order_id': data.get('id'),
                            'bictorys_payment_status': 'pending',
                        })
                        _logger.info(
                            "Bictorys: order created for POS order %s → bictorys_id=%s",
                            self.name, data.get('id'),
                        )
                        break
                    else:
                        retry += 1
                except Exception as e:
                    _logger.exception(
                        "Bictorys: exception during order creation for %s: %s",
                        self.name, e,
                    )
                    retry += 1

    @api.model
    def bictorys_get_order_status(self, pos_reference):
        """Called by POS JS polling to check payment status."""
        order = self.search([('pos_reference', '=', pos_reference)], limit=1)
        _logger.info(
            "Bictorys: bictorys_get_order_status(%s) → %s",
            pos_reference,
            order.bictorys_payment_status if order else 'not found',
        )
        return order.bictorys_payment_status or False if order else False

    @api.model
    def bictorys_cancel_order(self, pos_reference):
        """Called by POS JS when the cashier cancels."""
        order = self.search([('pos_reference', '=', pos_reference)], limit=1)
        if not order or not order.bictorys_order_id:
            return

        provider = self.env['payment.provider'].sudo().search(
            [('code', '=', 'bictorys'), ('state', '!=', 'disabled')], limit=1
        )
        if not provider:
            return

        api_base = (
            'https://api.test.bictorys.com'
            if provider.state == 'test'
            else 'https://api.bictorys.com'
        )
        url = f"{api_base}/order-management/v1/orders/{order.bictorys_order_id}"
        try:
            requests.delete(
                url,
                headers={'accept': 'application/json', 'X-API-Key': provider.sudo().bictorys_secret_key},
                timeout=10,
            )
            order.write({'bictorys_payment_status': 'failed'})
            _logger.info("Bictorys: cancelled order %s", order.bictorys_order_id)
        except Exception as e:
            _logger.exception("Bictorys: cancel error: %s", e)

    @api.model
    def bictorys_check_after_validation(self, pos_reference):
        order = self.search([('pos_reference', '=', pos_reference)], limit=1)

        if not order:
            return {'status': 'not_found'}

        if not order.bictorys_order_id:
            return {'status': 'not_created'}

        return {
            'status': 'ok',
            'bictorys_order_id': order.bictorys_order_id,
            'payment_status': order.bictorys_payment_status,
        }