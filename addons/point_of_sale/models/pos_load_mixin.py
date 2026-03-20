# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.fields import Domain
from odoo.exceptions import AccessError


class PosLoadMixin(models.AbstractModel):
    _name = 'pos.load.mixin'
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_search_read(self, data, config):
        """ Search and return records to be loaded in the pos """
        if not config:
            raise ValueError("config must be provided to search for PoS data.")

        domain = self._server_date_to_domain(self._load_pos_data_domain(data, config))
        if domain is False:
            return []

        records = self.search(domain)
        return self._load_pos_data_read(records, config)

    @api.model
    def _load_pos_data_domain(self, data, config):
        """ Return the domain used to filter records """
        return []

    @api.model
    def _server_date_to_domain(self, domain):
        """ Optionally restrict the domain to records modified after the last server sync """
        if domain is False:
            return domain

        last_server_date = self.env.context.get('pos_last_server_date', False)
        limited_loading = self.env.context.get('pos_limited_loading', True)
        model_included = self._name not in ['pos.session', 'pos.config']

        if limited_loading and last_server_date and model_included:
            domain = Domain.AND([domain, [('write_date', '>', last_server_date)]])

        return domain

    @api.model
    def _load_pos_data_read(self, records, config):
        """ Read specific fields from the given records """
        if not config:
            raise ValueError("config must be provided to read PoS data.")

        fields = self._load_pos_data_fields(config)
        records = records._filtered_access("read").read(fields, load=False)
        return records or []

    def _unrelevant_records(self, config):
        unrelevant_record_ids = []
        for record in self:
            try:
                if not record.active:
                    unrelevant_record_ids.append(record.id)
            except AccessError:
                # If the user has no read access, consider the record as unrelevant
                unrelevant_record_ids.append(record.id)
        return unrelevant_record_ids

    @api.model
    def _load_pos_data_fields(self, config):
        """ Return the list of fields to be loaded """
        return []
