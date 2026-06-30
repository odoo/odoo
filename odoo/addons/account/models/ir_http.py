# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        result['is_quick_edit_mode_enabled'] = self.env.user._is_internal() and self.env.company.quick_edit_mode
        return result
