# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from openerp.tools import float_compare, float_is_zero
from openerp import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Matching Number")

    @api.model
    def compute_full_after_batch_reconcile(self):
        super(AccountMoveLine, self).compute_full_after_batch_reconcile()
        #check if the reconcilation is full
        partial_rec_set = self.env['account.partial.reconcile']
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        currency = False
        for aml in self:
            total_debit += aml.debit
            total_credit += aml.credit
            if not currency and aml.currency_id:
                currency = aml.currency_id
            if aml.currency_id and aml.currency_id == currency:
                total_amount_currency += aml.amount_currency
                partial_rec_set |= aml.matched_debit_ids | aml.matched_credit_ids
        partial_rec_ids = [x.id for x in list(partial_rec_set)]
        #if the total debit and credit are equal, and the total amount in currency is 0, the reconciliation is full
        digits_rounding_precision = self[0].company_id.currency_id.rounding
        if float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0 \
          and (not currency or float_is_zero(total_amount_currency, precision_rounding=currency.rounding)):
            #in that case, mark the reference on the partial reconciliations and the entries
            self.env['account.full.reconcile'].with_context(check_move_validity=False).create({
                'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                'reconciled_line_ids': [(6, 0, self.ids)]})


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Full Reconcile")

    @api.model
    def create(self, vals):
        res = super(AccountPartialReconcile, self).create(vals)
        if self._context.get('skip_full_reconcile_check'):
            #when running the manual reconciliation wizard, don't check the partials separately for full
            #reconciliation or exchange rate because it is handled manually after the whole processing
            return res
        #check if the reconcilation is full
        #first, gather all journal items involved in the reconciliation just created
        partial_rec_set = OrderedDict.fromkeys([x for x in res])
        aml_set = self.env['account.move.line']
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        currency = None
        for partial_rec in partial_rec_set:
            if currency is None:
                currency = partial_rec.currency_id
            for aml in [partial_rec.debit_move_id, partial_rec.credit_move_id]:
                if aml not in aml_set:
                    total_debit += aml.debit
                    total_credit += aml.credit
                    aml_set |= aml
                    if aml.currency_id and aml.currency_id == currency:
                        total_amount_currency += aml.amount_currency
                for x in aml.matched_debit_ids | aml.matched_credit_ids:
                    partial_rec_set[x] = None
        partial_rec_ids = [x.id for x in partial_rec_set.keys()]
        aml_ids = [x.id for x in aml_set]
        #then, if the total debit and credit are equal, or the total amount in currency is 0, the reconciliation is full
        digits_rounding_precision = aml_set[0].company_id.currency_id.rounding
        if float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0 \
          or (currency and float_is_zero(total_amount_currency, precision_rounding=currency.rounding)):

            #in that case, mark the reference on the partial reconciliations and the entries
            self.env['account.full.reconcile'].with_context(check_move_validity=False).create({
                'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                'reconciled_line_ids': [(6, 0, aml_ids)]})
        return res

    @api.multi
    def unlink(self):
        """When removing a partial reconciliation, also unlink its full reconciliation if it exists"""
        for rec in self:
            if rec.full_reconcile_id:
                rec.full_reconcile_id.unlink()
        return super(AccountPartialReconcile, self).unlink()


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _description = "Full Reconcile"

    name = fields.Char(string='Number', required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('account.reconcile'))
    partial_reconcile_ids = fields.One2many('account.partial.reconcile', 'full_reconcile_id', string='Reconciliation Parts')
    reconciled_line_ids = fields.One2many('account.move.line', 'full_reconcile_id', string='Matched Journal Items')
