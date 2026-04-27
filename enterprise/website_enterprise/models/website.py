# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def is_website_generator_available(self):
        return self.env['ir.config_parameter'].sudo().get_param('website_generator.enable', False)
