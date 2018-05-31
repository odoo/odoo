import logging

from odoo import models, _
from odoo.exceptions import UserError, except_orm
from odoo.tools import float_is_zero


_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _fast_reconcile(self, amls):
        debit_amls = amls.filtered(lambda aml: aml.debit > 0 and not aml.reconciled)
        credit_amls = amls.filtered(lambda aml: aml.credit > 0 and not aml.reconciled)
        company_ids = set([a.company_id.id for a in amls])
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries!'))
        all_accounts = [a.account_id for a in amls]
        if len(set(all_accounts)) > 1:
            raise UserError(_('Entries are not of the same account!'))
        if not (all_accounts[0].reconcile or all_accounts[0].internal_type == 'liquidity'):
            raise UserError(_('The account %s (%s) is not marked as reconciliable !') % (all_accounts[0].name, all_accounts[0].code))
        company_id = debit_amls and debit_amls[0].company_id
        company_currency_id = company_id.currency_id
        # Ensure that this is a full reconciliation
        sum_debit = sum([a.debit for a in debit_amls])
        sum_credit = sum([a.credit for a in credit_amls])
        # If reconciliation is not total or that all moves don't have same currency, skip, it won't be reconciled at all
        # So user will have to do it himself
        if not float_is_zero(sum_debit - sum_credit, precision_rounding=company_currency_id.rounding):
            return
        if len(set([a.currency_id for a in amls])) > 1:
            return
        currency_id = debit_amls and debit_amls[0].currency_id
        if currency_id.id:
            currency_id = currency_id.id
        else:
            currency_id = None

        full_reconcile = self.env['account.full.reconcile'].create({})
        while True:
            if not debit_amls.ids or not credit_amls.ids:
                break
            debit = debit_amls[0]
            credit = credit_amls[0]
            amount = min(debit.amount_residual, credit.amount_residual)
            amount_currency = min(debit.amount_currency, credit.amount_currency)

            vals = (debit.id, credit.id, amount, amount_currency, currency_id, company_id.id, full_reconcile.id)

            if float_is_zero(debit.amount_residual - amount, precision_rounding=company_currency_id.rounding):
                debit_amls = debit_amls[1:]
            else:
                debit_amls[0].amount_residual -= amount
                debit_amls[0].amount_residual_currency -= amount_currency
            if float_is_zero(credit.amount_residual - amount, precision_rounding=company_currency_id.rounding):
                credit_amls = credit_amls[1:]
            else:
                credit_amls[0].amount_residual -= amount
                credit_amls[0].amount_residual_currency -= amount_currency
            # Create partial reconcile
            self.env.cr.execute('''INSERT INTO account_partial_reconcile
                    (debit_move_id, credit_move_id, amount, amount_currency, currency_id, company_id, full_reconcile_id) VALUES (%s, %s, %s, %s, %s, %s, %s)''', vals)

        # update account_move_line
        self.env.cr.execute('UPDATE account_move_line SET reconciled=%s, amount_residual=0, amount_residual_currency=0, full_reconcile_id=%s WHERE id IN %s', (True, full_reconcile.id, tuple(amls.ids)))

    def _reconcile_payments(self):
        reconcile_by_partner = {}
        invoices = self.env['account.invoice']
        for order in self:
            aml = order.statement_ids.mapped('journal_entry_ids') | order.account_move.line_ids | order.invoice_id.move_id.line_ids
            if order.invoice_id:
                invoices += order.invoice_id
            aml = aml.filtered(lambda r: not r.reconciled and r.account_id.internal_type == 'receivable' and r.partner_id == order.partner_id.commercial_partner_id)
            partner = len(aml) > 1 and aml[0].partner_id and aml[0].partner_id.id or False
            if reconcile_by_partner.get(partner):
                reconcile_by_partner[partner] = reconcile_by_partner[partner] | aml
            else:
                reconcile_by_partner[partner] = aml
        try:
            for k, v in reconcile_by_partner.items():
                self._fast_reconcile(v)
            # Validate invoice
            self.invalidate_cache()
            for inv in invoices:
                inv._compute_residual()
                inv._compute_payments()
            _logger.info(_('POS Session AML fast-reconciled using new algorithm'))
        except except_orm:
            raise
        except:
            _logger.warning(_('Error when trying to fast-reconcile POS Session move lines; falling back to standard code'))
            return super(PosOrder, self)._reconcile_payments()
