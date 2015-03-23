# -*- coding: utf-8 -*-

from openerp import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def _claim_count_out(self):
    	Claim = self.env['crm.claim']
        for picking in self:
            picking.claim_count_out = Claim.search_count([('ref', '=', ('stock.picking,' + str(picking.id)))])

    claim_count_out = fields.Integer(compute='_claim_count_out', string='Claims')
