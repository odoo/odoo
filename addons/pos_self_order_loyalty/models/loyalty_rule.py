# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    @api.model
    def _load_pos_self_data_fields(self, config):
        # `code` is declared so that the client can hold it, but its value is only sent by
        # /pos-self-order/check-card-code, to whoever entered it (see _load_pos_self_data_read)
        return [field for field in super()._load_pos_self_data_fields(config) if field != 'promo_barcode']

    @api.model
    def _load_pos_self_data_read(self, records, config):
        # With the public mobile access token, anyone could read the codes and apply them
        read_records = super()._load_pos_self_data_read(records, config)
        for read_record in read_records:
            read_record.pop('code', None)
        return read_records
