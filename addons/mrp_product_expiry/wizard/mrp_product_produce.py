# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def do_produce(self):
        confirm_expired_lots = self._check_expired_lots()
        if confirm_expired_lots:
            return confirm_expired_lots
        return super(MrpProductProduce, self).do_produce()

    def _check_expired_lots(self):
        # We use the 'dont_check_expired' context key to avoid to make the check
        # when user did already confirmed the wizard about using expired lots.
        if self.env.context.get('dont_check_expired'):
            return False
        expired_lot_ids = []
        for line in self.raw_workorder_line_ids:
            if line.lot_id and line.lot_id.product_expiry_alert:
                expired_lot_ids += [line.lot_id.id]
        if expired_lot_ids:
            return {
                'name': _('Confirmation'),
                'type': 'ir.actions.act_window',
                'res_model': 'expiry.picking.confirmation',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_produce_id': self.id,
                    'default_lot_ids': [(6, 0, expired_lot_ids)],
                }
            }
