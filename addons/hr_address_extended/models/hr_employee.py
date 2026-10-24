from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    private_city_id = fields.Many2one(
        'res.city',
        string='Private City ID', groups="hr.group_hr_user", tracking=1,
        compute="_compute_private_city_id",
        inverse="_inverse_private_city_id",
        readonly=False, store=True, index='btree_not_null',
        domain="[('country_id', '=?', private_country_id), ('state_id', '=?', private_state_id)]")
    private_country_enforce_cities = fields.Boolean(
        related='private_country_id.enforce_cities', groups="hr.group_hr_user", readonly=True)

    @api.depends('private_state_id')
    def _compute_private_city_id(self):
        for employee in self:
            if employee.private_city_id and employee.private_state_id and employee.private_city_id.state_id != employee.private_state_id:
                employee.private_city_id = False

    def _inverse_private_city_id(self):
        for employee in self:
            if employee.private_city_id:
                employee.private_state_id = employee.private_city_id.state_id
                employee.private_city = employee.private_city_id.name
                employee.private_zip = employee.private_city_id.zipcode

    @api.onchange('private_city_id')
    def _onchange_private_city_id(self):
        self._inverse_private_city_id()
