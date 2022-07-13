# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrAsset(models.Model):
    _inherit = 'ir.asset'

    def _get_active_addons_list_skip_theme(self):
        if request and request.session.get('project_sharing'):
            return True
        return super()._get_active_addons_list_skip_theme()
