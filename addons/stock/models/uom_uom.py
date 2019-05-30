# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_model_to_check(self):
        res = super(UoM, self)._get_model_to_check()
        res.append({
            'model': 'stock.move.line',
            'field': 'product_uom_id',
            'domain': [('state', '!=', 'cancel')],
            'msg': _("Some products have already been moved or are currently reserved.")})
        res.append({
            'model': 'stock.inventory.line',
            'field': 'product_uom_id',
            'domain': [('inventory_id.state', '!=', 'cancel')],
            'msg': _("Some products have already been inventoried.")})
        return res

    def _adjust_uom_quantities(self, qty, quant_uom):
        """ This method adjust the quantities of a procurement if its UoM isn't the same
        as the one of the quant and the parameter 'propagate_uom' is not set.
        """
        procurement_uom = self
        computed_qty = qty
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
            computed_qty = self._compute_quantity(qty, quant_uom, rounding_method='HALF-UP')
            procurement_uom = quant_uom
        return (computed_qty, procurement_uom)
