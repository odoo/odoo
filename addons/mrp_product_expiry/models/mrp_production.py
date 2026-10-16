# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def pre_button_mark_done(self):
        confirm_expired_lots = self._check_expired_lots()
        if confirm_expired_lots:
            return confirm_expired_lots
        return super().pre_button_mark_done()

    def _check_expired_lots(self):
        # We use the 'skip_expired' context key to avoid to make the check when
        # user already confirmed the wizard about using expired lots.
        if self.env.context.get('skip_expired'):
            return False
        expired_move_line_ids = self.move_raw_ids.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert).ids
        if expired_move_line_ids:
            return {
                'name': _('Confirmation'),
                'type': 'ir.actions.act_window',
                'res_model': 'expiry.picking.confirmation',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'new',
                'context': self._get_expired_context(expired_move_line_ids),
            }

    def _get_expired_context(self, expired_move_line_ids):
        context = dict(self.env.context)
        context.update({
            'default_move_line_ids': [Command.set(expired_move_line_ids)],
            'default_production_ids': self.ids,
        })
        return context
