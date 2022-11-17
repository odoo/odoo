# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    batch_group_by_carrier = fields.Boolean('Carrier', help="Automatically group batches by carriers")
    batch_max_weight = fields.Integer("Maximum weight per batch",
                                      help="A transfer will not be automatically added to batches that will exceed this weight if the transfer is added to it.\n"
                                           "Leave this value as '0' if no weight limit.")
    weight_uom_id = fields.Many2one('uom.uom', string='Weight unit of measure', compute='_compute_weight_uom_id')

    def _compute_weight_uom_id(self):
        self.weight_uom_id = self.env.company.default_weight_uom_id

    @api.model
    def _get_batch_group_by_keys(self):
        return super()._get_batch_group_by_keys() + ['batch_group_by_carrier']


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_possible_pickings_domain(self):
        domain = super()._get_possible_pickings_domain()
        if self.picking_type_id.batch_group_by_carrier:
            domain = expression.AND([domain, [('carrier_id', '=', self.carrier_id.id if self.carrier_id else False)]])

        return domain

    def _get_possible_batches_domain(self):
        domain = super()._get_possible_batches_domain()
        if self.picking_type_id.batch_group_by_carrier:
            domain = expression.AND([domain, [('picking_ids.carrier_id', '=', self.carrier_id.id if self.carrier_id else False)]])

        return domain

    def _is_auto_batchable(self, picking=None):
        """ Verifies if a picking can be put in a batch with another picking without violating auto_batch constrains.
        """
        res = super()._is_auto_batchable(picking)
        if not picking:
            picking = self.env['stock.picking']
        if self.picking_type_id.batch_max_weight:
            res = res and (self.weight + picking.weight <= self.picking_type_id.batch_max_weight)
        return res
