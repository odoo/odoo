# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_view_field_attributes(self):
        keys = super()._get_view_field_attributes()
        keys.append('sanitize')
        keys.append('sanitize_tags')
        return keys
