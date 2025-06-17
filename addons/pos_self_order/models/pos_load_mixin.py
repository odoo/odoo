# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosLoadMixin(models.AbstractModel):
    _inherit = "pos.load.mixin"

    @api.model
    def _load_pos_self_data_search_read(self, data, config):
        """ Search and return records to be loaded in the self """
        if not config:
            raise ValueError("config must be provided to search for PoS data.")

        domain = self._load_pos_self_data_domain(data, config)
        if domain is False:
            return []

        records = self.search(domain)
        return self._load_pos_self_data_read(records, config)

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        """ Return the domain used to filter records """
        return self._load_pos_data_domain(data, config)

    @api.model
    def _load_pos_self_data_read(self, records, config):
        """ Read specific fields from the given records """
        if not config:
            raise ValueError("config must be provided to read PoS data.")

        fields = self._load_pos_self_data_fields(config)
        records = records.read(fields, load=False)
        return records or []

    @api.model
    def _load_pos_self_data_fields(self, config):
        """ Return the list of fields to be loaded """
        return self._load_pos_data_fields(config)
