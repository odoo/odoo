# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_model_to_check(self):
        res = super(UoM, self)._get_model_to_check()
        res.append({
            'model': 'account.invoice.line',
            'field': 'uom_id',
            'domain': [('invoice_id.state', '!=', 'cancel')],
            'msg': _("Some products have already been invoiced.")})
        res.append({
            'model': 'account.move.line',
            'field': 'product_uom_id',
            'domain': [('move_id.state', '!=', 'draft')],
            'msg': _("Some products have already been recorded.")})
        return res
