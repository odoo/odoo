# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import models, api


class PosLoadMixin(models.AbstractModel):
    _name = "pos.load.mixin"
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_fields(self, config_id: int):
        return []

    @api.model
    def _load_pos_data_domain(self, data):
        return []

    # If you need to adapt the data to be loaded in the PoS, you can
    # override this method in your model.
    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }

    def write(self, vals):
        # origin_pos_config_id = vals.get('origin_pos_config_id')
        # if(vals.get('origin_pos_config_id')):
        #     del vals['origin_pos_config_id']
        # sessions = self.env['pos.session'].sudo().search([('state', 'in', ['opened', 'opening_control']), ('config_id', '!=', origin_pos_config_id)])
        # for session in sessions:
        #     config = session.config_id
        #     loaded_data = json.loads(session.loaded_data) if session.loaded_data else session.load_data({})
        #     watched_ids = [item['id'] for item in loaded_data[self._name]['data']]
        #     ids = list(set(self.ids).intersection(watched_ids))
        #     if len(ids) == 0:
        #         continue
        #     watched_fields = loaded_data[self._name]['fields']
        #     fields = set(vals.keys()).intersection(watched_fields) if watched_fields else list(vals.keys())
        #     if len(fields) == 0:
        #         continue
        #     config._notify('DATA_CHANGED', {'model': self._name, 'ids': ids, 'fields': fields} )
        return super().write(vals)



    def unlink(self):
        sessions = self.env['pos.session'].sudo().search([('state', 'in', ['opened', 'opening_control'])])
        for session in sessions:
            config = session.config_id
            loaded_data = json.loads(session.loaded_data) if session.loaded_data else session.load_data({})
            watched_ids = [item['id'] for item in loaded_data[self._name]['data']]
            ids = list(set(self.ids).intersection(watched_ids))
            if len(ids) == 0:
                continue
            config._notify('DATA_UNLINKED', {'model': self._name, 'ids': ids} )
        return super().unlink()
