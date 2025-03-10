# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
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
        domain = self._server_date_to_domain(self._load_pos_data_domain(data))
        fields = self._load_pos_data_fields(data['pos.config'][0]['id'])
        return self.search_read(domain, fields, load=False) if domain is not False else []

    def _server_date_to_domain(self, domain):
        last_server_date = self.env.context.get('pos_last_server_date', False)
        limited_loading = self.env.context.get('pos_limited_loading', True)
        if last_server_date and domain is not False and limited_loading:
            domain = AND([domain, [('write_date', '>', last_server_date)]])
        return domain

    def _post_read_pos_data(self, data):
        return data

    def _read_pos_record(self, ids, config_id):
        fields = self._load_pos_data_fields(self.id)
        return self.with_context(config_id=config_id)._post_read_pos_data(self.browse(ids).read(fields, load=False))
