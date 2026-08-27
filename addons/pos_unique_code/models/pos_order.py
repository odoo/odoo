# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from .pos_unique_code import CODE_LENGTH


class PosOrder(models.Model):
    _inherit = 'pos.order'

    unique_code = fields.Char(
        string="Order Code",
        size=CODE_LENGTH,
        copy=False,
        help="The one-time code the customer used to confirm this order. "
             "It stays empty when the cashier validated the order without a code.",
    )

    def _load_pos_self_data_fields(self, config):
        # The kiosk loads an explicit whitelist, unlike the PoS which loads every field.
        return super()._load_pos_self_data_fields(config) + ['unique_code']

    def _check_pos_order(self, pos_config, order, device_type, table=None):
        values = super()._check_pos_order(pos_config, order, device_type, table)
        # The kiosk payload is public, so only keep a code that really exists.
        code = (order.get('unique_code') or '').strip()
        if code and pos_config.env['pos.unique.code'].sudo().search_count(
            [('unique_code', '=', code)], limit=1
        ):
            values['unique_code'] = code
        return values

    @api.model
    def _load_pos_preparation_data_fields(self):
        return super()._load_pos_preparation_data_fields() + ['unique_code']
