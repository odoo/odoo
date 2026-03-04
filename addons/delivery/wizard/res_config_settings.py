# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_install_more_provider(self):
        return self.env['delivery.carrier'].install_more_provider()
