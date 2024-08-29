# -*- coding: utf-8 -*-
from odoo.addons import point_of_sale
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosConfig(models.Model, point_of_sale.PosConfig):

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
        return super().open_ui()
