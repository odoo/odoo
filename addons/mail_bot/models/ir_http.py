# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = ['ir.http']

    def session_info(self):
        res = super().session_info()
        if self.env.user._is_internal():
            res['odoobot_initialized'] = self.env.user.odoobot_state not in [False, 'not_initialized']
        return res
