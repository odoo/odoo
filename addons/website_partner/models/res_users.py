# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.private
    def get_website_meta_i18n_value(self, field_name, lang_code):
        return self.partner_id.get_website_meta_i18n_value(field_name, lang_code)
