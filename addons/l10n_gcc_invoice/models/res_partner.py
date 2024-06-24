# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_partner_lang_direction(self):
        self.ensure_one()
        return self.env['res.lang']._lang_get_direction(self.lang)
