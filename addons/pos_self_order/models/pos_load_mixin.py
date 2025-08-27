# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class PosLoadMixin(models.AbstractModel):
    _inherit = "pos.load.mixin"

    @api.model
    def _load_pos_self_data_domain(self, data):
        """ Return the domain used to filter records """
        return self._load_pos_data_domain(data)

    @api.model
    def _load_pos_self_data_read(self, records, config):
        """ Read specific fields from the given records """
        if not config:
            raise ValueError("config must be provided to read PoS data.")

        fields = self._load_pos_self_data_fields(config)
        if fields and 'write_date' not in fields:
            fields.append('write_date')
        records = records.read(fields, load=False)
        return records or []

    @api.model
    def _load_pos_self_data_fields(self, config):
        """ Return the list of fields to be loaded """
        return self._load_pos_data_fields(config)

    @api.model
    def _load_pos_self_data_domain_and_relations(self, data):
        adapted_data = {model: d['records'] for model, d in data.items()}
        fields = self._load_pos_self_data_fields(data["pos.config"]["records"][0] if data.get("pos.config") else None)
        return {
            'domain': self._load_pos_self_data_domain(adapted_data),
            'fields': fields,
            'relations': self._load_data_relations(fields),
        }

    @api.model
    def _load_pos_self_metadata(self, data, search_params={}):
        result = self._load_pos_self_data_domain_and_relations(data)
        data[self._name] = {
            **result,
            'records': self.search(domain=search_params.get('domain', False) or result['domain'],
                                   limit=search_params.get('limit', False),
                                   offset=search_params.get('offset', 0))
        }
        return data

    @api.model
    def _read_pos_self_data_from_metadata(self, server_data, config_id):
        response = {}
        for model, data in server_data.items():
            try:
                records = data['records']
                response[model] = {
                    **data,
                    'records': records._load_pos_self_data_read(records, config_id) if len(records) > 0 else [],
                }
                del response[model]['domain']
            except AccessError as e:
                response[model] = []
                _logger.info("Could not load model %s due to AccessError: %s", model, e)

        return response
