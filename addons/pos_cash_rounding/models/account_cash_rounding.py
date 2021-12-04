# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    loss_account_id = fields.Many2one('account.account', string='Loss Account')

    def _get_loss_account_id(self):
        return self.loss_account_id or super(AccountCashRounding, self)._get_loss_account_id()

    @api.constrains('rounding', 'rounding_method', 'strategy')
    def _check_session_state(self):
        open_session = self.env['pos.session'].search_count([('config_id.rounding_method', '=', self.id), ('state', '!=', 'closed')])
        if open_session:
            raise ValidationError(
                _("You are not allowed to change the cash rounding configuration while a pos session using it is already opened."))
