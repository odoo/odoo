# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError

ERR_MSG = _("You cannot modify a %s in order for its posted data to be updated. It is the law. Field: %s")


class AccountMove(models.Model):

    _inherit = "account.move"

    def button_cancel(self):
        try:
            super(AccountMove, self).button_cancel()
        except UserError:
            raise UserError(_('You cannot modify a posted entry of a journal.'))


class AccountJournal(models.Model):

    _inherit = "account.journal"

    @api.multi
    def write(self, vals):
        if vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))

        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name))

        return super(AccountJournal, self).create(vals)
