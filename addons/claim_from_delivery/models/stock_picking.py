# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    claim_count_out = fields.Integer(compute='_compute_claim_count_out', string='Claims')

    def _compute_claim_count_out(self):
        claim = self.env['crm.claim']
        for picking in self:
            picking.claim_count_out = claim.search_count([('ref', '=', ('stock.picking,' + str(picking.id)))])
