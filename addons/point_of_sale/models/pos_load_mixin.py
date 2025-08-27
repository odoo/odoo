# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from math import floor


class PosLoadMixin(models.AbstractModel):
    _name = 'pos.load.mixin'
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_domain(self, data):
        """ Return the domain used to filter records """
        return []

    @api.model
    def _load_pos_data_fields(self, config):
        """ Return the list of fields to be loaded """
        return []

    @api.model
    def _load_pos_data_read(self, records, config):
        """ Read specific fields from the given records """
        if not config:
            raise ValueError("config must be provided to read PoS data.")

        fields = self._load_pos_data_fields(config)
        if fields and 'write_date' not in fields:
            fields.append('write_date')
        records = records.read(fields, load=False)
        return records or []

    @api.model
    def _load_pos_data_dependencies(self):
        return []

    @api.model
    def _load_data_relations(self, fields):
        model_fields = self._fields
        relations = {}

        for name, params in model_fields.items():
            if (len(fields) and name not in fields) or (not len(fields) and params.manual):
                continue

            if params.comodel_name:
                relations[name] = {
                    'name': name,
                    'model': params.model_name,
                    'compute': bool(params.compute),
                    'related': bool(params.related),
                    'relation': params.comodel_name,
                    'type': params.type,
                }
                if params.type == 'many2one' and params.ondelete:
                    relations[name]['ondelete'] = params.ondelete
                if params.type == 'one2many' and params.inverse_name:
                    relations[name]['inverse_name'] = params.inverse_name
                if params.type == 'many2many':
                    relations[name]['relation_table'] = params.relation
            else:
                relations[name] = {
                    'name': name,
                    'type': params.type,
                    'compute': bool(params.compute),
                    'related': bool(params.related),
                }

        return relations

    @api.model
    def load_pos_data_force_loading(self):
        """ Override this method to force loading of all records of this model
        each time the POS starts (ignoring the local cache).
        """
        return False

    @api.model
    def _load_pos_data_domain_and_dependencies(self, data):
        adapted_data = {model: d['records'] for model, d in data.items()}
        fields = self._load_pos_data_fields(data["pos.config"]["records"] if data.get("pos.config") else None)
        return {
            'domain': self._load_pos_data_domain(adapted_data),
            'dependencies': self._load_pos_data_dependencies(),
            'fields': fields,
            'relations': self._load_data_relations(fields),
        }

    @api.model
    def _load_pos_metadata(self, data, search_params={}):
        result = self._load_pos_data_domain_and_dependencies(data)
        data[self._name] = {
            **result,
            'records': self.search(domain=search_params.get('domain', False) or result['domain'],
                                   limit=search_params.get('limit', False),
                                   offset=search_params.get('offset', 0))
        }
        return data

    @api.model
    def _read_pos_data_from_metadata(self, server_data, local_data, config_id):
        model = self._name
        if model in local_data['models'] and model in local_data['records'] and len(local_data['records'][model]):
            ids = local_data['records'][model].keys()
            # Timestamp in python is giving timestamp in seconds.
            # Timestamp in JS is giving timestamp in milliseconds.
            # We multiply by 1000 to compare both in milliseconds.
            records = server_data['records'].filtered(lambda x: self.load_pos_data_force_loading() or not str(x.id) in ids or (x.write_date and floor(x.write_date.timestamp()) > local_data['records'][model][str(x.id)]))
        else:
            records = server_data['records']
        return {
            **server_data,
            'records': records._load_pos_data_read(records, config_id) if len(records) > 0 else [],
        }
