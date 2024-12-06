from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = ['res.users', 'pos.load.mixin']

    role = fields.Selection([('manager', 'Manager'), ('cashier', 'Cashier')], string='Role', compute='_compute_role')

    @api.depends('groups_id')
    def _compute_role(self):
        for user in self:
            user.role = 'manager' if self.env.ref('point_of_sale.group_pos_manager') in user.groups_id else 'cashier'

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', self.env.uid)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'partner_id', 'groups_id']

    def _load_pos_data(self, data):
        user = super()._load_pos_data(data)
        if user:
            user[0]['role'] = 'manager' if data['pos.config'][0]['group_pos_manager_id'] in user[0]['groups_id'] else 'cashier'
            del user[0]['groups_id']
        return user
