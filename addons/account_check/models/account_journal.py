##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    checkbook_ids = fields.One2many('account.checkbook', 'journal_id', 'Checkbooks')
    show_checkbooks = fields.Boolean(compute='_compute_show_checkbooks')

    @api.depends('outbound_payment_method_ids.code', 'type')
    def _compute_show_checkbooks(self):
        for rec in self:
            rec.show_checkbooks = rec.type == 'bank' and any(
                x.code == 'new_own_checks' for x in rec.outbound_payment_method_ids)

    @api.model
    def create(self, vals):
        rec = super(AccountJournal, self).create(vals)
        own_checks = self.env.ref('account_check.account_payment_method_new_own_checks')
        if (own_checks in rec.outbound_payment_method_ids and not rec.checkbook_ids):
            rec._create_checkbook()
        return rec

    def _create_checkbook(self):
        """ Create a checkbook for the journal """
        for rec in self:
            rec.checkbook_ids.create({'journal_id': rec.id, 'state': 'active'})

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        res |= self.env.ref('account_check.account_payment_method_new_own_checks')
        return res

    def _default_inbound_payment_methods(self):
        res = super()._default_inbound_payment_methods()
        res |= self.env.ref('account_check.account_payment_method_in_own_checks')
        return res

    @api.depends('type')
    def _compute_outbound_payment_method_ids(self):
        super()._compute_outbound_payment_method_ids()
        for journal in self:
            if journal.type == 'cash':
                check_method = self.env.ref('account_check.account_payment_method_new_own_checks')
                journal.outbound_payment_method_ids -= check_method

    @api.depends('type')
    def _compute_inbound_payment_method_ids(self):
        super()._compute_inbound_payment_method_ids()
        for journal in self:
            if journal.type == 'cash':
                check_method = self.env.ref('account_check.account_payment_method_in_own_checks')
                journal.inbound_payment_method_ids -= check_method
