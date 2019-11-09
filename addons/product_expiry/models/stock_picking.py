# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _pre_action_done_hook(self):
        res = super()._pre_action_done_hook()
        # We use the 'skip_expired' context key to avoid to make the check when
        # user did already confirmed the wizard about expired lots.
        if res is True and not self.env.context.get('skip_expired'):
            pickings_to_warn_expired = self._check_expired_lots()
            if pickings_to_warn_expired:
                return pickings_to_warn_expired._action_generate_expired_wizard()
        return res

    def _check_expired_lots(self):
        expired_pickings = self.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert).picking_id
        return expired_pickings

    def _action_generate_expired_wizard(self):
        expired_lot_ids = self.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert).lot_id.ids
        context = dict(self.env.context)
        context.update({
            'default_picking_ids': [(6, 0, self.ids)],
            'default_lot_ids': [(6, 0, expired_lot_ids)],
        })
        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'res_model': 'expiry.picking.confirmation',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }
