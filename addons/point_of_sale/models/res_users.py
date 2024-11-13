from odoo import models, api


class ResUsers(models.Model):
    _inherit = ['res.users', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', self.env.uid)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'partner_id', 'all_group_ids']

    def _load_pos_data(self, data):
        user = super()._load_pos_data(data)
        if user:
            user[0]['role'] = 'manager' if data['pos.config'][0]['group_pos_manager_id'] in user[0]['all_group_ids'] else 'cashier'
            del user[0]['all_group_ids']
        return user
