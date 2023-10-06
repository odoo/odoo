# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_translation_frontend_modules_name(self):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['portal_rating']
