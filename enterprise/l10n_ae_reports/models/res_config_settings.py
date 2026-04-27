# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_country_codes_with_another_tax_closing_start_date(self):
        return super()._get_country_codes_with_another_tax_closing_start_date() | {'AE'}
