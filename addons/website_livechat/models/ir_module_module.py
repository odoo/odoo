# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _frontend_roots(self):
        return super()._frontend_roots() + ['im_livechat']
