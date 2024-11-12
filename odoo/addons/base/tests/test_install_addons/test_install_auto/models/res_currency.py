# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _test_install_auto_cron(self):
        return True
