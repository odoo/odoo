# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.fields import Datetime
from odoo.osv.expression import AND


class PosLoadMixin(models.AbstractModel):
    _name = 'pos.load.mixin'
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_fields(self, config_id):
        return []

    @api.model
    def _load_pos_data_domain(self, data):
        return []

    # If you need to adapt the data to be loaded in the PoS, you can
    # override this method in your model.
    def _load_pos_data(self, data):
        # Deprecated
        # Kept for backward compatibility.
        domain = self._server_date_to_domain(self._load_pos_data_domain(data))
        fields = self._load_pos_data_fields(data['pos.config'][0]['id'])
        return self.search_read(domain, fields, load=False) if domain is not False else []

    def _server_date_to_domain(self, domain):
        # Deprecated
        # Kept for backward compatibility.
        last_server_date = self.env.context.get('pos_last_server_date', False)
        limited_loading = self.env.context.get('pos_limited_loading', True)
        if last_server_date and domain is not False and limited_loading:
            domain = AND([domain, [('write_date', '>', last_server_date)]])
        return domain

    def _unrelevant_records(self):
        # Deprecated
        # Kept for backward compatibility.
        return self.filtered(lambda record: not record.active).ids

    def _post_read_pos_data(self, data):
        return data

    def _read_pos_record(self, ids, config_id):
        # Deprecated
        # Kept for backward compatibility.
        fields = self._load_pos_data_fields(self.id)
        record_ids = self.browse(ids).exists()
        if not record_ids:
            return []
        return self.with_context(config_id=config_id)._post_read_pos_data(record_ids.read(fields, load=False))

    # New loading behavior
    @api.model
    def _load_pos_data_dependencies(self):
        return []

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
    def _load_pos_data_relations(self, fields):
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
    def _load_pos_data_domain_and_dependencies(self, data):
        adapted_data = {model: d['records'] for model, d in data.items() if model in data}
        fields = self._load_pos_data_fields(data["pos.config"]["records"][0].id if data.get("pos.config") else None)
        return {
            'domain': self._load_pos_data_domain(adapted_data),
            'dependencies': self._load_pos_data_dependencies(),
            'fields': fields,
            'relations': self._load_pos_data_relations(fields),
        }

    @api.model
    def _read_pos_data_from_metadata(self, server_data, local_data, config_id):
        model = self._name
        fields = server_data['fields']
        if fields and 'write_date' not in fields:
            fields.append('write_date')
        if model in local_data['models'] and model in local_data['records'] and len(local_data['records'][model]):
            ids = local_data['records'][model].keys()
            records = server_data['records'].filtered(lambda x: not str(x.id) in ids or (x.write_date and x.write_date.replace(microsecond=0) > Datetime.from_string(local_data['records'][model][str(x.id)])))
        else:
            records = server_data['records']
        del server_data['domain']
        return {
            **server_data,
            'records': records.with_context(config_id=config_id)._post_read_pos_data(records._read_record(fields)) if len(records) > 0 else [],
        }

    def _read_record(self, fields, load=False):
        return self.read(fields, load=load)
