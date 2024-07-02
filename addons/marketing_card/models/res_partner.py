from odoo import models


class Partner(models.Model):
    _inherit = 'res.partner'

    def _marketing_card_allowed_field_paths(self):
        return [
            'display_name', 'name',
            'email', 'mobile', 'phone',
            'country_id', 'country_id.display_name', 'country_id.name',
        ]
