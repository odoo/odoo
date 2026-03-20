# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

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
        expired_pickings = self.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert or (ml.removal_date and ml.removal_date <= datetime.datetime.now())).picking_id
        return expired_pickings

    def _action_generate_expired_wizard(self):
        expired_lot_ids = self.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert or (ml.removal_date and ml.removal_date <= datetime.datetime.now())).lot_id.ids
        view_id = self.env.ref('product_expiry.confirm_expiry_view').id
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
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }
