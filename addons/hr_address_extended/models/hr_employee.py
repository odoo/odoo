from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.onchange('private_city_id')
    def _onchange_private_city_id(self):
        for record in self:
            if record.private_city_id:
                record.private_state_id = record.private_city_id.state_id
                record.private_city = record.private_city_id.name
                record.private_zip = record.private_city_id.zipcode
