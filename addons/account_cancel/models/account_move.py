# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.multi
    def button_cancel(self):
        for move in self:
            if not move.journal_id.update_posted:
                raise UserError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
        if self.ids:
            self._check_lock_date()
            self._cr.execute('''
                UPDATE account_move
                SET state=%s
                WHERE id IN %s''', ('draft', tuple(self.ids),))
            self.invalidate_cache()
        self._check_lock_date()
        return True
