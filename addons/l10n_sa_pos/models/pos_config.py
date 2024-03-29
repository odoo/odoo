# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class pos_config(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
        return super(pos_config, self).open_ui()
