# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_model_to_check(self):
        res = super(UoM, self)._get_model_to_check()
        res.append({
            'model': 'mrp.bom.line',
            'field': 'product_uom_id',
            'domain': [('bom_id.active', '=', True)],
            'msg': _("Some products have already been used in a bills of material.")})
        return res
