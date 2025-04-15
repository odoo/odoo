from odoo import models, api


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.users', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', self.env.uid)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'partner_id', 'all_group_ids']

    def _post_read_pos_data(self, data):
        config_id = self.env['pos.config'].browse(self.env.context.get('config_id'))
        if data:
            data[0]['role'] = 'manager' if self.env.ref('point_of_sale.group_pos_manager').id in data[0]['all_group_ids'] else 'cashier'
            del data[0]['all_group_ids']
        return super()._post_read_pos_data(data)
