from odoo import models, api


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.users', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', '=', self.env.uid)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'partner_id', 'all_group_ids']

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if read_records:
            read_records[0]['role'] = 'manager' if config.group_pos_manager_id.id in read_records[0]['all_group_ids'] else 'cashier'
            del read_records[0]['all_group_ids']
        return read_records
