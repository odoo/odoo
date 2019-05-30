# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_model_to_check(self):
        res = super(UoM, self)._get_model_to_check()
        res.append({
            'model': 'purchase.order.line',
            'field': 'product_uom',
            'domain': [('state', '!=', 'cancel')],
            'msg': _("Some products have already been purchased.")})
        return res
