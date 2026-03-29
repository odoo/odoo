# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import requests

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('bictorys', 'Bictorys')]

    bictorys_terminal_identifier = fields.Char(
        string="Terminal / Device ID",
        copy=False,
    )
    bictorys_latest_response = fields.Char(
        copy=False,
        groups='base.group_erp_manager',
    )

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {'bictorys_latest_response'})

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['bictorys_terminal_identifier']
        return params

    def bictorys_create_order(self, order_data):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()
        secret_key, api_base = self._bictorys_get_api_config()
        if not secret_key:
            _logger.error("Bictorys: bictorys_create_order — no secret_key found")
            return {'error': 'No active Bictorys provider configured.'}
        url = f"{api_base}/order-management/v1/orders"
        headers = {'accept': 'application/json', 'content-type': 'application/json', 'X-API-Key': secret_key}
        _logger.info("Bictorys: bictorys_create_order — payload:\n%s", pprint.pformat(order_data))
        try:
            response = requests.post(url, json=order_data, headers=headers, timeout=10)
            _logger.info("Bictorys: bictorys_create_order — HTTP %s body: %s", response.status_code, response.text)
            if response.status_code == 201:
                return response.json()
            return {'error': response.text, 'status_code': response.status_code}
        except Exception as e:
            _logger.exception("Bictorys: bictorys_create_order — exception: %s", e)
            return {'error': str(e)}

    def bictorys_cancel_order(self, bictorys_order_id):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()
        secret_key, api_base = self._bictorys_get_api_config()
        if not secret_key:
            return False
        url = f"{api_base}/order-management/v1/orders/{bictorys_order_id}"
        try:
            response = requests.delete(url, headers={'accept': 'application/json', 'X-API-Key': secret_key}, timeout=10)
            _logger.info("Bictorys: bictorys_cancel_order %s — HTTP %s", bictorys_order_id, response.status_code)
            return response.status_code in (200, 204)
        except Exception as e:
            _logger.exception("Bictorys: bictorys_cancel_order — exception: %s", e)
            return False

    def bictorys_get_latest_response(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()
        latest = self.sudo().bictorys_latest_response
        _logger.info("Bictorys: bictorys_get_latest_response — value: %s", latest)
        return json.loads(latest) if latest else False

    def _bictorys_get_api_config(self):
        self.ensure_one()
        provider = self.env['payment.provider'].sudo().search(
            [('code', '=', 'bictorys'), ('state', '!=', 'disabled')], limit=1
        )
        if not provider:
            _logger.warning("Bictorys: _bictorys_get_api_config — no active provider")
            return None, None
        api_base = 'https://api.test.bictorys.com' if provider.state == 'test' else 'https://api.bictorys.com'
        _logger.info("Bictorys: _bictorys_get_api_config — state=%s api_base=%s", provider.state, api_base)
        return provider.sudo().bictorys_secret_key, api_base