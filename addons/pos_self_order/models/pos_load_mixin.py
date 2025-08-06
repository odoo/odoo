# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosLoadMixin(models.AbstractModel):
    _inherit = "pos.load.mixin"

    @api.model
    def _load_pos_self_data_domain(self, data):
        return self._load_pos_data_domain(data)

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        return self._load_pos_data_fields(config_id)

    def _load_pos_self_data(self, data):
        domain = self._load_pos_self_data_domain(data)
        fields = self._load_pos_self_data_fields(data['pos.config'][0]['id'])
        return self.search_read(domain, fields, load=False) if domain is not False else []

    def _post_read_pos_self_data(self, data):
        return data

    @api.model
    def _load_pos_self_data_domain_and_dependencies(self, data):
        adapted_data = {model: d['records'] for model, d in data.items() if model in data}
        fields = self._load_pos_self_data_fields(data["pos.config"]["records"][0].id if data.get("pos.config") else None)
        return {
            'domain': self._load_pos_self_data_domain(adapted_data),
            'fields': fields,
            'relations': self._load_pos_data_relations(fields),
        }

    @api.model
    def _load_pos_self_metadata(self, data, search_params={}):
        result = self._load_pos_self_data_domain_and_dependencies(data)
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
            fields = data['fields']
            if fields and 'write_date' not in fields:
                fields.append('write_date')
            records = data['records']
            response[model] = {
                **data,
                'records': records.with_context(config_id=config_id)._post_read_pos_self_data(records.read(fields, load=False)) if len(records) > 0 else [],
            }

        return response
