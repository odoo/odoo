# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        nomenclature = self.env.company.nomenclature_id
        if nomenclature.is_gs1_nomenclature:
            res['gs1_group_separator_encodings'] = nomenclature.gs1_separator_fnc1
        return res
