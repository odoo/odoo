# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError

ERR_MSG = _("You cannot modify a %s in order for its posted data to be updated or deleted. It is the law. Field: %s")


class AccountMove(models.Model):

    _inherit = "account.move"

    @api.multi
    def write(self, vals):
        allowed_fields = set(['ref', 'narration', 'line_ids'])
        forbidden_fields = set(self.fields_get_keys()) - allowed_fields
        if (self.company_id.country_id == self.env.ref('base.fr') and
            self.state == "posted" and
            len(set(vals.keys()) & forbidden_fields) > 0):

            raise UserError(ERR_MSG % (self._name, str(forbidden_fields)))
        return super(AccountMove, self).write(vals)

    @api.multi
    def unlink(self):
        if (self.company_id.country_id == self.env.ref('base.fr') and
            self.state == "posted"):
            raise UserError(ERR_MSG % (self._name, self._name))
        return super(AccountMove, self).unlink()

    def button_cancel(self):
        try:
            super(AccountMove, self).button_cancel()
        except UserError:
            raise UserError(_('You cannot modify a posted entry of a journal.'))


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    @api.multi
    def write(self, vals):
        allowed_fields = set(['ref',
                             'narration',
                             'blocked',
                             'date_maturity',
                             'analytic_line_ids',
                             'analytic_account_id',
                             'analytic_tag_ids',
                             'user_type_id',
                             'tax_exigible',
                             'move_id'])

        forbidden_fields = set(self.fields_get_keys()) - allowed_fields
        if (self.company_id.country_id == self.env.ref('base.fr') and
            self.move_id.state == "posted" and
            len(set(vals.keys()) & forbidden_fields) > 0):

            raise UserError(ERR_MSG % self._name, str(forbidden_fields))
        return super(AccountMoveLine, self).write(vals)

    @api.multi
    def unlink(self):
        if (self.company_id.country_id == self.env.ref('base.fr') and
            self.move_id.state == "posted"):
            raise UserError(ERR_MSG % (self._name, self._name))
        return super(AccountMoveLine, self).unlink()


class AccountJournal(models.Model):

    _inherit = "account.journal"

    @api.multi
    def write(self, vals):
        if self.company_id.country_id == self.env.ref('base.fr') and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))
        vals.update({'update_posted': False})

        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        if self.company_id.country_id == self.env.ref('base.fr') and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))

        return super(AccountJournal, self).create(vals)


class BankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.multi
    def button_draft(self):
        if not self.state = 'confirm'
            self.state = 'open'
