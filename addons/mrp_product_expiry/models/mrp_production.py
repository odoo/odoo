# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class MrpWorkorder(models.Model):
    _inherit = 'mrp.production'

    def _pre_button_mark_done(self):
        confirm_expired_lots = self._check_expired_lots()
        if confirm_expired_lots:
            return confirm_expired_lots
        return super()._pre_button_mark_done()

    def _check_expired_lots(self):
        # We use the 'skip_expired' context key to avoid to make the check when
        # user already confirmed the wizard about using expired lots.
        if self.env.context.get('skip_expired'):
            return False
        expired_lot_ids = self.move_raw_ids.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert).lot_id.ids
        if expired_lot_ids:
            return {
                'name': _('Confirmation'),
                'type': 'ir.actions.act_window',
                'res_model': 'expiry.picking.confirmation',
                'view_mode': 'form',
                'target': 'new',
                'context': self._get_expired_context(expired_lot_ids),
            }

    def _get_expired_context(self, expired_lot_ids):
        context = dict(self.env.context)
        context.update({
            'default_lot_ids': [(6, 0, expired_lot_ids)],
            'default_production_ids': self.ids,
        })
        return context
