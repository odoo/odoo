from odoo import api, fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    private_city_id = fields.Many2one(
        'res.city',
        string='Private City ID', groups="hr.group_hr_user", tracking=1,
        compute="_compute_private_city_id",
        inverse="_inverse_private_city_id",
        readonly=False, store=True,
        domain="[('country_id', '=?', private_country_id), ('state_id', '=?', private_state_id)]")
    private_country_enforce_cities = fields.Boolean(
        related='private_country_id.enforce_cities', groups="hr.group_hr_user", readonly=True)

    @api.depends('private_state_id')
    def _compute_private_city_id(self):
        for record in self:
            if record.private_city_id and record.private_state_id and record.private_city_id.state_id != record.private_state_id:
                record.private_city_id = False

    def _inverse_private_city_id(self):
        for record in self:
            if record.private_city_id:
                record.private_state_id = record.private_city_id.state_id
                record.private_city = record.private_city_id.name
                record.private_zip = record.private_city_id.zipcode
