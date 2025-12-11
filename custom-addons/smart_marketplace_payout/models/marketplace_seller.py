# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MarketplaceSeller(models.Model):
    _inherit = 'marketplace.seller'

    # Payout fields added by this module
    payout_batch_ids = fields.One2many(
        'marketplace.payout.batch',
        'seller_id',
        string='Payout Batches',
    )
    total_payouts = fields.Integer(
        string='Total Payouts',
        compute='_compute_total_payouts',
    )
    
    def _compute_total_payouts(self):
        for seller in self:
            seller.total_payouts = len(seller.payout_batch_ids)
    
    def action_view_payouts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payouts'),
            'res_model': 'marketplace.payout.batch',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('seller_id', '=', self.id)],
            'target': 'current',
        }

