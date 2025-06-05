# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.osv.expression import AND


class PosLoadMixin(models.AbstractModel):
    _name = 'pos.load.mixin'
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_fields(self, config_id=None):
        return []

    @api.model
    def _load_pos_data_domain(self, data, config_id=None):
        return []

    @api.model
    def _load_pos_data_search_read(self, data, config_id):
        if not config_id:
            raise ValueError("config_id must be provided to search for PoS data.")

        domain = self._server_date_to_domain(self._load_pos_data_domain(data, config_id))
        if domain is False:
            return []

        records = self.search(domain)
        return self._load_pos_data_read(records, config_id)

    @api.model
    def _load_pos_data_read(self, records, config_id):
        if not config_id:
            raise ValueError("config_id must be provided to read PoS data.")

        fields = self._load_pos_data_fields(config_id)
        records = records.read(fields, load=False)
        return records or []

    @api.model
    def _server_date_to_domain(self, domain):
        excluded_models = ['pos.session', 'pos.config']
        last_server_date = self.env.context.get('pos_last_server_date', False)
        limited_loading = self.env.context.get('pos_limited_loading', True)

        if last_server_date and domain is not False and limited_loading and self._name not in excluded_models:
            domain = AND([domain, [('write_date', '>', last_server_date)]])

        return domain

    def _unrelevant_records(self):
        return self.filtered(lambda record: not record.active).ids
