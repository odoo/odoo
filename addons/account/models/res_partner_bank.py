# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    journal_id = fields.One2many('account.journal', 'bank_account_id', domain=[('type', '=', 'bank')], string='Account Journal', readonly=True,
        help="The accounting journal corresponding to this bank account.")

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for bank in self:
            if len(bank.journal_id) > 1:
                raise ValidationError(_('A bank account can belong to only one journal.'))

    def default_get(self, fields_list):
        if 'acc_number' not in fields_list:
            return super().default_get(fields_list)

        # When create & edit, `name` could be used to pass (in the context) the
        # value input by the user. However, we want to set the default value of
        # `acc_number` variable instead.
        default_acc_number = self._context.get('default_acc_number', False) or self._context.get('default_name', False)
        return super(ResPartnerBank, self.with_context(default_acc_number=default_acc_number)).default_get(fields_list)
