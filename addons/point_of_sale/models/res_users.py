from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

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
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        user = self.search_read(domain, fields, load=False)
        del user[0]['groups_id']
        return {
            'data': user,
            'fields': fields,
        }
