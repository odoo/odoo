# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError

ERR_MSG = _("You cannot modify a %s in order for its posted data to be updated. It is the law. Field: %s")


class AccountMove(models.Model):

    _inherit = "account.move"

    def write(self, vals):
        allowed_fields = set('ref', 'narration', 'line_ids')
        forbidden_fields = set(self.fields_get_keys()) - allowed_fields
        if (self.company_id.country_id == self.env.ref('base.fr') and
            self.state == "posted" and
            vals.keys() in forbidden_fields):

            raise UserError(ERR_MSG % self._name, str(forbidden_fields))
        return super(AccountMove, self).write(vals)

    def button_cancel(self):
        try:
            super(AccountMove, self).button_cancel()
        except UserError:
            raise UserError(_('You cannot modify a posted entry of a journal.'))


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    def write(self, vals):
        allowed_fields = set('ref',
                             'narration',
                             'blocked',
                             'date_maturity',
                             'analytic_line_ids',
                             'analytic_account_id',
                             'analytic_tag_ids',
                             'user_type_id',
                             'tax_exigible',
                             'move_id')

        forbidden_fields = set(self.fields_get_keys()) - allowed_fields
        if (self.company_id.country_id == self.env.ref('base.fr') and
            self.move_id.state == "posted" and
            vals.keys() in forbidden_fields):

            raise UserError(ERR_MSG % self._name, str(forbidden_fields))
        return super(AccountMoveLine, self).write(vals)


class AccountJournal(models.Model):

    _inherit = "account.journal"

    @api.multi
    def write(self, vals):
        if self.env.user.company_id.country_id == self.env.ref('base.fr') and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))
        vals.update({'update_posted': False})

        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        if self.env.user.company_id.country_id == self.env.ref('base.fr') and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))

        return super(AccountJournal, self).create(vals)
