# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import AccessError


class Website(models.Model):
    _inherit = "website"

    some_translatable_field = fields.Char(string="A translatable field",
                                          translate=True, default='something')

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['test']:
            result.append(self.env['test.model']._search_get_detail(self, order, options))
        return result
