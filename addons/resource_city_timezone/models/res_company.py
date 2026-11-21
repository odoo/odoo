# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_address_tz(self):
        return super()._get_address_tz() or self.env['res.city']._get_city_timezone(
            self.country_id, self.city, self.state_id,
        )
