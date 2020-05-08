# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def check(self, mode, values=None):
        res = super().check(mode=mode, values=values)
        self._check_account_move(mode, values=values)
        return res

    def _check_account_move(self, mode, values=None):
        # Prevent unlink journal entry attachment
        if self.env.is_superuser():
            return True
        if mode == 'unlink' and self:
            self.env['ir.attachment'].flush(['res_model', 'res_id'])
            self.env.cr.execute(
                '''
                SELECT am.id
                FROM account_move AS am
                LEFT JOIN ir_attachment ir ON (ir.res_id = am.id)
                WHERE am.state = 'posted'
                AND  ir.res_model = 'account.move' AND ir.id IN %s
                LIMIT 1
                ''',
                (tuple(self.ids),))
            if self.env.cr.fetchone():
                raise UserError(_('You cannot delete an attachment of a posted journal entry.'))
