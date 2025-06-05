# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosLoadMixin(models.AbstractModel):
    _inherit = "pos.load.mixin"

    @api.model
    def _load_pos_self_data_domain(self, data, config_id=None):
        return self._load_pos_data_domain(data, config_id)

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        return self._load_pos_data_fields(config_id)

    @api.model
    def _load_pos_self_data_search_read(self, data, config_id):
        if not config_id:
            raise ValueError("config_id must be provided to search for PoS data.")

        domain = self._load_pos_self_data_domain(data, config_id)
        if domain is False:
            return []

        records = self.search(domain)
        return self._load_pos_self_data_read(records, config_id)

    @api.model
    def _load_pos_self_data_read(self, records, config_id):
        if not config_id:
            raise ValueError("config_id must be provided to read PoS data.")

        fields = self._load_pos_self_data_fields(config_id)
        records = records.read(fields, load=False)
        return records or []
