# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'
    
    def action_pos_session_close(self):
        """Bypass the ORM to create the bank statement move lines for the POS payments."""
        # normal verification but the confirmation is now done using an ORM bypass
        try:
            for session in self:
                company_id = session.config_id.company_id.id
                ctx = dict(self.env.context, force_company=company_id, company_id=company_id)
                for st in session.statement_ids:
                    if abs(st.difference) > st.journal_id.amount_authorized_diff:
                        # The pos manager can close statements with maximums.
                        if not self.env['ir.model.access'].check_groups("point_of_sale.group_pos_manager"):
                            raise UserError(_("Your ending balance is too different from the theoretical cash closing (%.2f), the maximum allowed is: %.2f. You can contact your manager to force it.") % (st.difference, st.journal_id.amount_authorized_diff))
                    if (st.journal_id.type not in ['bank', 'cash']):
                        raise UserError(_("The type of the journal for your payment method should be bank or cash "))
                    st.with_context(ctx).sudo()._pos_statement_confirm()
            _logger.info('Payments AML fast-created using ORM bypass')
        except:
            _logger.warning('Error when trying to fast create payments AML; falling back to standard code')
        # carry on
        return super(PosSession, self).action_pos_session_close()

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _fast_reconcile(self, amls):
        debit_amls = amls.filtered(lambda aml: aml.debit > 0)
        credit_amls = amls.filtered(lambda aml: aml.credit > 0)
        company_id = debit_amls and debit_amls[0].company_id
        company_currency_id = company_id.currency_id
        # Ensure that this is a full reconciliation
        sum_debit = sum([a.debit for a in debit_amls])
        sum_credit = sum([a.credit for a in credit_amls])
        # If reconciliation is not total or that all moves don't have same currency, skip, it won't be reconciled at all
        # So user will have to do it himself
        if not float_is_zero(sum_debit-sum_credit, precision_rounding=company_currency_id.rounding):
            return
        if len(set([a.currency_id for a in amls])) > 1:
            return
        currency_id = debit_amls and debit_amls[0].currency_id
        if currency_id.id:
            currency_id = currency_id.id
        else:
            currency_id = None
        partial_reconcile_ids = []
        full_reconcile = self.env['account.full.reconcile'].create({})
        test = []
        while True:
            if not debit_amls.ids or not credit_amls.ids:
                break
            debit = debit_amls[0]
            credit = credit_amls[0]
            amount = min(debit.amount_residual, credit.amount_residual)
            amount_currency = min(debit.amount_currency, credit.amount_currency)

            vals = (debit.id, credit.id, amount, amount_currency, currency_id, company_id.id, full_reconcile.id)
            test.append(vals)
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
        try:
            reconcile_by_partner = {}
            invoices = self.env['account.invoice']
            for order in self:
                aml = order.statement_ids.mapped('journal_entry_ids').mapped('line_ids') | order.account_move.line_ids | order.invoice_id.move_id.line_ids
                if order.invoice_id:
                    invoices += order.invoice_id
                aml = aml.filtered(lambda r: not r.reconciled and r.account_id.internal_type == 'receivable' and r.partner_id == order.partner_id.commercial_partner_id)
                partner = len(aml) > 1 and aml[0].partner_id and aml[0].partner_id.id or False
                if reconcile_by_partner.get(partner):
                    reconcile_by_partner[partner] = reconcile_by_partner[partner] | aml
                else:
                    reconcile_by_partner[partner] = aml
            for k,v in reconcile_by_partner.items():
                self._fast_reconcile(v)
            # Validate invoice
            self.invalidate_cache()
            for inv in invoices:
                inv._compute_residual()
                inv._compute_payments()
            _logger.info('POS Session AML fast-reconciled using new algorithm')
        except:
            _logger.warning('Error when trying to fast-reconcile POS Session move lines; falling back to standard code')
            return super(PosOrder, self)._reconcile_payments()

