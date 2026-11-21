# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def get_website_meta_i18n_value(self, field_name, lang_code):
        return self.partner_id.get_website_meta_i18n_value(field_name, lang_code)
