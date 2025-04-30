from odoo import api, models


class IrModuleModule(models.Model):
    _name = 'ir.module.module'
    _inherit = 'ir.module.module'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'state']

    @api.model
    def _load_pos_data_domain(self):
        return [('name', '=', 'pos_settle_due')]

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain()
        fields = self._load_pos_data_fields(data['pos.config'][0]['id'])
        return self.search_read(domain, fields, load=False)

    def _post_read_pos_data(self, data):
        return data

    def _read_pos_record(self, ids, config_id):
        fields = self._load_pos_data_fields(self.id)
        return self.browse(ids).read(fields, load=False)
