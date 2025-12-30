# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict

from datetime import date
import json

class AccountPartialReconcile(models.Model):
    _name = 'account.partial.reconcile'
    _description = "Partial Reconcile"

    # ==== Reconciliation fields ====
    debit_move_id = fields.Many2one(
        comodel_name='account.move.line',
        index=True, required=True)
    credit_move_id = fields.Many2one(
        comodel_name='account.move.line',
        index=True, required=True)
    full_reconcile_id = fields.Many2one(
        comodel_name='account.full.reconcile',
        string="Full Reconcile", copy=False, index='btree_not_null')
    exchange_move_id = fields.Many2one(comodel_name='account.move', index='btree_not_null')

    # this field will be used upon the posting of the invoice, to know if we can keep the partial or if the
    # user has to re-do entirely the reconciliaion (in  case fundamental values changed for the cash basis)
    draft_caba_move_vals = fields.Json(string="Values that created the draft cash-basis entry")

    # ==== Currency fields ====
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Company Currency",
        related='company_id.currency_id',
        help="Utility field to express amount currency")
    debit_currency_id = fields.Many2one(
        comodel_name='res.currency',
        store=True,
        related='debit_move_id.currency_id', precompute=True,
        string="Currency of the debit journal item.")
    credit_currency_id = fields.Many2one(
        comodel_name='res.currency',
        store=True,
        related='credit_move_id.currency_id', precompute=True,
        string="Currency of the credit journal item.")

    # ==== Amount fields ====
    amount = fields.Monetary(
        currency_field='company_currency_id',
        help="Always positive amount concerned by this matching expressed in the company currency.")
    debit_amount_currency = fields.Monetary(
        currency_field='debit_currency_id',
        help="Always positive amount concerned by this matching expressed in the debit line foreign currency.")
    credit_amount_currency = fields.Monetary(
        currency_field='credit_currency_id',
        help="Always positive amount concerned by this matching expressed in the credit line foreign currency.")

    # ==== Other fields ====
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company", store=True, readonly=False,
        precompute=True,
        compute='_compute_company_id')
    max_date = fields.Date(
        string="Max Date of Matched Lines", store=True,
        precompute=True,
        compute='_compute_max_date')
        # used to determine at which date this reconciliation needs to be shown on the aged receivable/payable reports

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('debit_currency_id', 'credit_currency_id')
    def _check_required_computed_currencies(self):
        bad_partials = self.filtered(lambda partial: not partial.debit_currency_id or not partial.credit_currency_id)
        if bad_partials:
            raise ValidationError(_("Missing foreign currencies on partials having ids: %s", bad_partials.ids))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('debit_move_id.date', 'credit_move_id.date')
    def _compute_max_date(self):
        for partial in self:
            partial.max_date = max(
                partial.debit_move_id.date,
                partial.credit_move_id.date
            )

    @api.depends('debit_move_id', 'credit_move_id')
    def _compute_company_id(self):
        for partial in self:
            # Potential exchange diff and caba entries should be created on the invoice side if any
            if partial.debit_move_id.move_id.is_invoice(True):
                partial.company_id = partial.debit_move_id.company_id
            else:
                partial.company_id = partial.credit_move_id.company_id

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def unlink(self):
        # OVERRIDE to unlink full reconcile linked to the current partials
        # and reverse the tax cash basis journal entries.

        # Avoid cyclic unlink calls when removing the partials that could remove some full reconcile
        # and then, loop again and again.
        if not self:
            return True

        # Get the payments without journal entry to reset once the amount residual is reset
        to_update_payments = self._get_to_update_payments(from_state='reconciled')
        # Retrieve the CABA entries to reverse.
        moves_to_reverse = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self.ids)])
        # Same for the exchange difference entries.
        moves_to_reverse += self.exchange_move_id

        # Retrieve the matching number to unlink
        full_to_unlink = self.full_reconcile_id

        # if the move is draft and can be removed, there is no need to update the matching number
        all_reconciled = self.debit_move_id + self.credit_move_id

        # Unlink partials before doing anything else to avoid 'Record has already been deleted' due to the recursion.
        res = super().unlink()

        # Remove the matching numbers before reversing the moves to avoid trying to remove the full twice.
        full_to_unlink.unlink()

        # Reverse or unlink CABA/exchange move entries.
        if moves_to_reverse:
            not_draft_moves = moves_to_reverse.filtered(lambda m: m.state != 'draft')
            draft_moves = moves_to_reverse - not_draft_moves
            default_values_list = [{
                'date': move._get_accounting_date(move.date, move._affect_tax_report()),
                'ref': move.env._('Reversal of: %s', move.name),
            } for move in not_draft_moves]
            not_draft_moves._reverse_moves(default_values_list, cancel=True)
            draft_moves.unlink()

        all_reconciled = all_reconciled.exists()
        self._update_matching_number(all_reconciled)
        to_update_payments.state = 'paid'
        return res

    @api.model_create_multi
    def create(self, vals_list):
        partials = super().create(vals_list)
        partials._get_to_update_payments(from_state='paid').state = 'reconciled'
        self._update_matching_number(partials.debit_move_id + partials.credit_move_id)
        return partials

    def _get_to_update_payments(self, from_state):
        to_update = []
        for partial in self:
            matched_payments = (partial.credit_move_id | partial.debit_move_id).move_id.matched_payment_ids
            to_check_payments = matched_payments.filtered(lambda payment: not payment.outstanding_account_id and payment.state == from_state)
            for payment in to_check_payments:
                if payment.payment_type == 'inbound':
                    amount = partial.debit_amount_currency
                else:
                    amount = -partial.credit_amount_currency
                if not payment.currency_id.compare_amounts(payment.amount_signed, amount):
                    to_update.append(payment)
                    break
        return self.env['account.payment'].union(*to_update)

    @api.model
    def _update_matching_number(self, amls):
        amls = amls._all_reconciled_lines()
        all_partials = amls.matched_debit_ids | amls.matched_credit_ids

        # The matchings form a set of graphs, which can be numbered: this is the matching number.
        # We iterate on each edge of the graphs, giving it a number (min of its edge ids).
        # By iterating, we either simply add a node (move line) to the graph and asign the number to
        # it or we merge the two graphs.
        # At the end, we have an index for the number to assign of all lines.
        number2lines = {}
        line2number = {}
        for partial in all_partials.sorted('id'):
            debit_min_id = line2number.get(partial.debit_move_id.id)
            credit_min_id = line2number.get(partial.credit_move_id.id)
            if debit_min_id and credit_min_id:  # merging the 2 graph into the one with smalles number
                if debit_min_id != credit_min_id:
                    min_min_id = min(debit_min_id, credit_min_id)
                    max_min_id = max(debit_min_id, credit_min_id)
                    for line_id in number2lines[max_min_id]:
                        line2number[line_id] = min_min_id
                    number2lines[min_min_id].extend(number2lines.pop(max_min_id))
            elif debit_min_id:  # adding a new node to a graph
                number2lines[debit_min_id].append(partial.credit_move_id.id)
                line2number[partial.credit_move_id.id] = debit_min_id
            elif credit_min_id:  # adding a new node to a graph
                number2lines[credit_min_id].append(partial.debit_move_id.id)
                line2number[partial.debit_move_id.id] = credit_min_id
            else:  # creating a new graph
                number2lines[partial.id] = [partial.debit_move_id.id, partial.credit_move_id.id]
                line2number[partial.debit_move_id.id] = partial.id
                line2number[partial.credit_move_id.id] = partial.id

        amls.flush_recordset(['full_reconcile_id'])
        self.env.cr.execute_values("""
            UPDATE account_move_line l
               SET matching_number = CASE
                       WHEN l.full_reconcile_id IS NOT NULL THEN l.full_reconcile_id::text
                       ELSE 'P' || source.number
                   END
              FROM (VALUES %s) AS source(number, ids)
             WHERE l.id = ANY(source.ids)
        """, list(number2lines.items()), page_size=1000)
        processed_amls = self.env['account.move.line'].browse([_id for ids in number2lines.values() for _id in ids])
        processed_amls.invalidate_recordset(['matching_number'])
        (amls - processed_amls).matching_number = False

    # -------------------------------------------------------------------------
    # RECONCILIATION METHODS
    # -------------------------------------------------------------------------

    def _calculate_paid_percentage(self, payment_partials, move_total_amount, foreign_currency):
        total_amount_paid = sum(
                                part.debit_amount_currency
                                if foreign_currency else part.amount
                                for part in payment_partials
                            )
        return total_amount_paid / move_total_amount

    def _recreate_payment_moves(self, payment_move):
        new_move = payment_move.copy({
            'state': 'draft',
            'name': False,
            'date': payment_move.date,
        })
        original_payment = payment_move.origin_payment_id
        new_payment = original_payment.copy({
        'state': 'draft',
        'move_id': new_move.id,
        'invoice_ids': [(6, 0, original_payment.invoice_ids.filtered(lambda inv: inv.state != 'cancel').ids)],
        })

        new_move.origin_payment_id = new_payment.id
        new_payment.action_post()

        invoices = new_payment.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
        if invoices:
            (new_move.line_ids + invoices.line_ids).filtered(
                lambda line:
                    line.account_id == new_payment.destination_account_id
                    and not line.reconciled,
            ).reconcile()

    def _reverse_payment_moves(self, move_values, lines_and_amount_to_adjust, previous_payment_partials, payment_moves, foreign_currency):
        '''Reverse payment moves linked to an invoice when a refund exceeds the remaining amount of one or more invoice lines.

        :param move_values:                   The result of 'account.move._collect_tax_cash_basis_values' for the invoice.
        :param lines_and_amount_to_adjust:    A dictionary mapping the invoice lines to the amount that must be adjusted.
        :param previous_payment_partials:     All the previous payment partials linked to the current invoice.
        :param payment_moves:                 An empty recordset to collect the payment moves to be reversed.
        :param foreign_currency:              A boolean indicating whether the move currency is different from the company's
                                              currency.
        :return:                              A recordset containing the payment moves that got reversed.
        '''

        payment_partial_to_reverse = []
        line_to_adjust, amount_to_adjust = max(
            lines_and_amount_to_adjust.items(),
            key=lambda item: item[1],
        )
        move_total_amount = move_values['total_amount_currency'] if foreign_currency else move_values['total_balance']
        for partial in previous_payment_partials:
            line_amount = abs(line_to_adjust.amount_currency if foreign_currency else line_to_adjust.balance)
            paid_percentage = self._calculate_paid_percentage(partial, move_total_amount, foreign_currency)
            amount_to_adjust -= line_amount * paid_percentage
            payment_partial_to_reverse.append(partial)
            if amount_to_adjust >= 0:
                break

        move_type = move_values['move'].move_type
        for partial in payment_partial_to_reverse:
            payment_move = partial.credit_move_id.move_id if move_type == 'out_invoice' else partial.debit_move_id.move_id
            default_vals = [{
                'date': payment_move.date,
                'ref': payment_move.env._('Reversal of: %s', payment_move.name),
            }]

            reversed_move = payment_move._reverse_moves(default_vals, cancel=True)
            payment_move._message_log_batch(
                bodies={
                    payment_move.id: payment_move.env._(
                        'This entry has been %s',
                        reversed_move._get_html_link(
                            title=payment_move.env._("reversed"),
                        ),
                    ),
                },
            )
            payment_moves |= payment_move

        return payment_moves

    def _set_excess_distribution_info_for_tax_cash_basis(self, excess_distribution_info):
        draft_caba_move_vals = {}
        if self.draft_caba_move_vals:
            draft_caba_move_vals = json.loads(self.draft_caba_move_vals)

        draft_caba_move_vals.setdefault('debit_excess_distribution_info', {})
        draft_caba_move_vals['debit_excess_distribution_info'].update(excess_distribution_info)
        self.draft_caba_move_vals = json.dumps(draft_caba_move_vals)

    def _distribute_excess_for_tax_cash_basis(
        self,
        excess_total_amount,
        processed_lines,
        to_process_lines,
        foreign_currency,
    ):
        def calculate_excess_payment_percentage():
            return excess_total_amount / abs(
                sum(
                    line.amount_currency if foreign_currency else line.balance
                    for _caba, line in excess_distribution_lines
                ),
            )

        indexed_tax_lines = {}
        excess_distribution_lines = set()
        excess_distribution_info = {}

        for line in processed_lines['tax']:
            tax_id = line.tax_line_id
            indexed_tax_lines[tax_id] = (line)

        for line, vals in processed_lines['base'].items():
            if vals.get('excess_causing_line', False):
                continue
            excess_distribution_lines.add(('base', line))
            for tax_id in line.tax_ids:
                excess_distribution_lines.add(('tax', indexed_tax_lines[tax_id]))
        excess_payment_percentage = calculate_excess_payment_percentage()
        for caba_treatment, line in list(excess_distribution_lines):
            vals = processed_lines[caba_treatment][line]
            line_excess_amount = abs(line.amount_currency) * excess_payment_percentage
            remaining_line_amount = vals['remaining_line_amount']

            if line.currency_id.compare_amounts(remaining_line_amount, line_excess_amount) < 0:
                excess_distribution_info[line.id] = remaining_line_amount
                to_process_lines[caba_treatment][line] = vals.get('refunded_line_amount', 0.0) + remaining_line_amount

                excess_total_amount -= remaining_line_amount
                excess_distribution_lines.remove((caba_treatment, line))
                excess_payment_percentage = calculate_excess_payment_percentage()

            else:
                to_process_lines[caba_treatment][line] = vals.get('refunded_line_amount', 0.0) + line_excess_amount
                excess_distribution_info[line.id] = line_excess_amount

        self._set_excess_distribution_info_for_tax_cash_basis(excess_distribution_info)
        return to_process_lines

    def _handle_fully_paid_refund_for_tax_cash_basis(self, line, current_refunded_line_amount, remaining_line_amount):
        excess_causing_line = False
        if line.currency_id.compare_amounts(abs(current_refunded_line_amount), remaining_line_amount) <= 0:
            return abs(current_refunded_line_amount), excess_causing_line

        excess_causing_line = True
        return remaining_line_amount, excess_causing_line

    def _handle_partially_paid_refund_for_tax_cash_basis(
        self,
        line,
        previous_payment_partials,
        current_refunded_line_amount,
        previous_refunded_total_amount,
        previous_excess_total_amount,
        remaining_line_amount,
        foreign_currency,
    ):
        excess_causing_line = False
        payment_amount_to_adjust = 0.0
        line_amount = abs(line.amount_currency if foreign_currency else line.balance)

        if line.currency_id.compare_amounts(abs(current_refunded_line_amount), remaining_line_amount) <= 0:
            refunded_line_amount = abs(current_refunded_line_amount)
            return refunded_line_amount, excess_causing_line, payment_amount_to_adjust

        max_refundable = line_amount - abs(previous_refunded_total_amount) - previous_excess_total_amount

        refunded_line_amount = abs(
            current_refunded_line_amount
            if line.currency_id.compare_amounts(abs(current_refunded_line_amount), max_refundable) <= 0
            else max_refundable,
        )

        if previous_payment_partials:
            payment_amount_to_adjust = refunded_line_amount - remaining_line_amount

        total_refunded_amount = abs(current_refunded_line_amount) + abs(previous_refunded_total_amount) + previous_excess_total_amount
        if line.currency_id.compare_amounts(line_amount, total_refunded_amount) < 0:
            excess_causing_line = True

        return refunded_line_amount, excess_causing_line, payment_amount_to_adjust

    def _process_refunded_lines_for_tax_cash_basis_values(
        self,
        move_values,
        partial,
        previous_payment_partials,
        current_refunded_lines,
        previous_refunded_lines,
        previous_excess_distribution_lines,
        paid_percentage,
        foreign_currency,
    ):
        def calculate_remaining_line_amount():
            return (
                (abs(line.amount_currency if foreign_currency else line.balance)
                - abs(previous_refunded_total_amount)
                - abs(previous_excess_total_amount)
                ) * (1 - paid_percentage)
            )

        def calculate_partial_payment_percentage():
            if foreign_currency:
                return partial.debit_amount_currency / (move_values['total_residual_currency'] + partial.debit_amount_currency)
            return partial.amount / (move_values['total_residual'] + partial.amount)

        to_process_lines = {
            'base': {},
            'tax': {},
        }
        processed_lines = {
            'base': {},
            'tax': {},
        }
        lines_and_paid_amount_to_adjust = {}
        partial_amount = partial.debit_amount_currency if foreign_currency else partial.amount
        partial_payment_percentage = calculate_partial_payment_percentage() if not current_refunded_lines else 0.0

        for caba_treatment, line in move_values['to_process_lines']:
            previous_refunded_total_amount = previous_refunded_lines[caba_treatment].get(line, 0.0) if previous_refunded_lines else 0.0
            previous_excess_total_amount = previous_excess_distribution_lines.get(str(line.id), 0.0) if previous_excess_distribution_lines else 0.0
            remaining_line_amount = calculate_remaining_line_amount()

            if remaining_line_amount <= 0:
                continue

            if current_refunded_lines:
                current_refunded_line_amount = current_refunded_lines[caba_treatment].get(line, 0.0)
                if not current_refunded_line_amount:
                    processed_lines[caba_treatment][line] = {
                        'remaining_line_amount': remaining_line_amount,
                    }
                    continue

                if not move_values['is_fully_paid']:
                    refunded_line_amount, excess_causing_line, payment_amount_to_adjust = \
                        self._handle_partially_paid_refund_for_tax_cash_basis(
                            line=line,
                            previous_payment_partials=previous_payment_partials,
                            current_refunded_line_amount=current_refunded_line_amount,
                            previous_refunded_total_amount=previous_refunded_total_amount,
                            previous_excess_total_amount=previous_excess_total_amount,
                            remaining_line_amount=remaining_line_amount,
                            foreign_currency=foreign_currency,
                        )
                    partial_amount -= refunded_line_amount
                    if payment_amount_to_adjust:
                        lines_and_paid_amount_to_adjust[line] = payment_amount_to_adjust
                    to_process_lines[caba_treatment][line] = refunded_line_amount
                    processed_lines[caba_treatment][line] = {
                        'excess_causing_line': excess_causing_line,
                        'remaining_line_amount': remaining_line_amount - refunded_line_amount,
                        'refunded_line_amount': refunded_line_amount,
                    }

                else:
                    refunded_line_amount, excess_causing_line = \
                        self._handle_fully_paid_refund_for_tax_cash_basis(line, current_refunded_line_amount, remaining_line_amount)

                    partial_amount -= abs(refunded_line_amount)
                    to_process_lines[caba_treatment][line] = refunded_line_amount
                    processed_lines[caba_treatment][line] = {
                        'excess_causing_line': excess_causing_line,
                        'remaining_line_amount': remaining_line_amount - refunded_line_amount,
                        'refunded_line_amount': refunded_line_amount,
                    }

            else:
                line_amount = remaining_line_amount * partial_payment_percentage
                to_process_lines[caba_treatment][line] = line_amount

        return to_process_lines, processed_lines, lines_and_paid_amount_to_adjust, partial_amount

    def _add_refund_info_to_tax_cash_basis_values(
        self,
        move_values,
        partial,
        previous_payment_partials,
        current_refunded_lines,
        previous_refunded_lines,
        previous_excess_distribution_lines,
        paid_percentage,
        foreign_currency,
    ):
        '''Add the refund information to the move_values dictionary to be used for tax cash basis.

        :param move_values:                         The result of 'account_move.collect_tax_cash_basis_values' for the current invoice.
        :param partial:                             The current partial reconcile record being processed.
        :param previous_payment_partials:           All the previous payment partials linked to the current invoice.
        :param current_refunded_lines:              The result of 'account_partial_reconcile._compute_refunded_lines_and_amount' for the
                                                    current move.
        :param previous_refunded_lines:             The result of 'account_partial_reconcile._compute_refunded_lines_and_amount' for the
                                                    past refund moves linked to the invoice.
        :param previous_excess_distribution_lines   The result of 'account_partial_reconcile._get_previous_excess_distribution_info' for
                                                    the past refund moves linked to the invoice.
        :param paid_percentage:                     The percentage of invoice already paid.
        :param foreign_currency:                    A boolean indicating whether the move currency is different from the company's
                                                    currency.
        :return:                                    The mutated move_values dictionary.
        '''
        to_process_lines, processed_lines, lines_and_amount_to_adjust, partial_amount = \
            self._process_refunded_lines_for_tax_cash_basis_values(
            move_values=move_values,
            partial=partial,
            previous_payment_partials=previous_payment_partials,
            current_refunded_lines=current_refunded_lines,
            previous_refunded_lines=previous_refunded_lines,
            previous_excess_distribution_lines=previous_excess_distribution_lines,
            paid_percentage=paid_percentage,
            foreign_currency=foreign_currency,
            )

        if not partial.company_currency_id.is_zero(partial_amount) and current_refunded_lines:
            to_process_lines = self._distribute_excess_for_tax_cash_basis(
                excess_total_amount=partial_amount,
                processed_lines=processed_lines,
                to_process_lines=to_process_lines,
                foreign_currency=foreign_currency,
            )

        payment_moves = self.env['account.move']
        if lines_and_amount_to_adjust:
            payment_moves = self._reverse_payment_moves(
                move_values, lines_and_amount_to_adjust, previous_payment_partials, payment_moves, foreign_currency,
            )
        if payment_moves:
            move_values['payment_moves_to_recreate'] = payment_moves

        move_values.update({
            'to_process_lines': [
                (
                    caba_treatment,
                    line,
                    line.currency_id.round((-1 if line.amount_currency < 0 else 1) * line_amount),
                )
                    for caba_treatment in ('base', 'tax')
                    for line, line_amount in to_process_lines[caba_treatment].items()
                ],
            })
        return move_values

    def _process_base_lines_for_tax_cash_basis(self, move_values, debit_base_lines, foreign_currency):
        '''Process the 'debit_base_lines' to extract the refunded lines and amount for tax cash basis entries.

        :param move_values:                 The result of 'account_move.collect_tax_cash_basis_values' for the current invoice.
        :param debit_base_lines:            The result of '_get_tax_cash_basis_base_lines' containing the base_lines of the
                                            debit move with the refund information under the 'discount_base_lines' key.
        :param foreign_currency:            A boolean indicating whether the move currency is different from the company's
                                            currency.
        :return:                            A dictionary mapping each refunded line to its refunded amount.
        '''
        to_process_lines = {
            'base': {},
            'tax': {},
        }
        manual_tax_amounts = {}
        for base_line in debit_base_lines:
            discount_base_lines = base_line.get('discount_base_lines', False)
            if not discount_base_lines:
                continue
            for discount_base_line in discount_base_lines:
                refunded_line_amount = discount_base_line['tax_details']['raw_total_excluded_currency'] \
                    if foreign_currency else discount_base_line['tax_details']['raw_total_excluded']
                to_process_lines['base'][base_line['record']] = to_process_lines['base'].get(base_line['record'], 0.0) + refunded_line_amount
                for tax_data in discount_base_line['tax_details']['taxes_data']:
                    tax = tax_data['tax']
                    refunded_tax_line_amount = tax_data['tax_amount_currency'] if foreign_currency else tax_data['tax_amount']
                    manual_tax_amounts[tax] = manual_tax_amounts.get(tax, 0.0) + refunded_tax_line_amount

        for caba_treatment, line in move_values['to_process_lines']:
            if caba_treatment != 'tax':
                continue
            refunded_tax_line_amount = manual_tax_amounts.get(line.tax_line_id)
            if refunded_tax_line_amount:
                to_process_lines['tax'][line] = refunded_tax_line_amount

        return to_process_lines

    def _get_base_lines_for_tax_cash_basis_values(self, move, refund_moves):
        '''Collect the updated base_lines of an invoice if a refund exists aganist it.

        :param move:                    The debit/credit move of the current partial reconcile record being processed.
        :param refund_moves:            A list containing the refund moves linked to the invoice.
        :return:                        The new base_lines of an invoice with the refund information added under the
                                        'discount_base_lines' key.
        '''

        AccountTax = self.env['account.tax']
        base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
        all_refund_base_lines = []
        for refund_move in refund_moves:
            refund_base_lines, _refund_tax_lines = refund_move._get_rounded_base_and_tax_lines()
            refund_base_lines = AccountTax._turn_base_lines_is_refund_flag_off(refund_base_lines)
            for refund_base_line in refund_base_lines:
                refund_base_line['special_type'] = 'global_discount'
            all_refund_base_lines.extend(refund_base_lines)

        company_id = self.company_id
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines + all_refund_base_lines, company_id)
        AccountTax._squash_global_discount_lines(base_lines, company_id)

        return base_lines

    def _compute_refunded_lines_and_amount(self, move_values, refund_moves, foreign_currency):
        '''Compute the refunded base and tax line amounts to be used for tax cash basis entries.'''

        if not refund_moves:
            return {}

        debit_base_lines = self._get_base_lines_for_tax_cash_basis_values(move_values['move'], refund_moves)
        return self._process_base_lines_for_tax_cash_basis(move_values, debit_base_lines, foreign_currency)

    def _get_previous_excess_distribution_info(self, previous_refund_partials):
        previous_excess_distribution_info = {}
        if not previous_refund_partials:
            return previous_excess_distribution_info

        for partial in previous_refund_partials:
            if not partial.draft_caba_move_vals:
                continue

            draft_caba_move_vals = json.loads(partial.draft_caba_move_vals)
            excess_distribution_info = draft_caba_move_vals.get('debit_excess_distribution_info') or {}
            for line_id, excess_line_amount in excess_distribution_info.items():
                previous_excess_distribution_info[line_id] = previous_excess_distribution_info.get(line_id, 0.0) + excess_line_amount

        return previous_excess_distribution_info

    def _get_moves_for_tax_cash_basis_values(self, move_values, partial):
        ''' Collect all the moves related to the current partial.

        :param move_values:     The result of 'account_move.collect_tax_cash_basis_values' for the current invoice.
        :param partial:         The current partial reconcile record being processed.
        :return:                A tuple of 4 elements:
            * current_refund_move:          A list containing the current refund move.
            * previous_refund_moves:        A list containing all the previous refund moves linked to the invoice.
            * previous_refund_partials:     A list containing all the previous refund partials linked to the invoice.
            * previous_payment_partials:    A list containing all the previous payment partials linked to the invoice.
        '''
        current_refund_move = []
        previous_refund_moves = []
        previous_refund_partials = []
        previous_payment_partials = []
        payment_term = move_values['payment_term']

        move_type = move_values['move'].move_type
        partials = payment_term.matched_credit_ids if move_type == 'out_invoice' else payment_term.matched_debit_ids
        for part in partials:
            refund_move = part.credit_move_id.move_id if move_type == 'out_invoice' else part.debit_move_id.move_id
            refund_move_values = refund_move._collect_tax_cash_basis_values()
            if part.id == partial.id and not refund_move_values:
                continue
            if part.id == partial.id and refund_move_values:
                current_refund_move.append(refund_move)
            elif refund_move_values:
                previous_refund_moves.append(refund_move)
                previous_refund_partials.append(part)
            else:
                previous_payment_partials.append(part)

        return current_refund_move, previous_refund_moves, previous_refund_partials, previous_payment_partials

    def _update_tax_cash_basis_values(self, move_values, partial):
        ''' Update the result of 'account_move.collect_tax_cash_basis_values' to include the information about
        refunds if they exist aganist an invoice.

        :return:                    The updated move_values dictionary with refund information passed as:
            *to_process_lines:      A list of tuples (caba_treatment, line, line_amount) where:
                                    - line_amount is the amount of the line to make the caba entry with.
        '''

        foreign_currency = move_values['currency'] != move_values['move'].company_id.currency_id
        move_total_amount = move_values['total_amount_currency'] if foreign_currency else move_values['total_balance']
        current_refund_move, previous_refund_moves, previous_refund_partials, previous_payment_partials = \
            self._get_moves_for_tax_cash_basis_values(move_values, partial)

        if current_refund_move or previous_refund_moves:
            if previous_payment_partials:
                refunded_total_amount = sum(
                    move.amount_total_in_currency_signed
                    if foreign_currency else move.amount_total
                    for move in previous_refund_moves
                )
                move_total_amount = move_total_amount - refunded_total_amount
                paid_percentage = self._calculate_paid_percentage(previous_payment_partials, move_total_amount, foreign_currency)
            else:
                paid_percentage = 0.0

            previous_excess_distribution_lines = self._get_previous_excess_distribution_info(previous_refund_partials)
            previous_refunded_lines = self._compute_refunded_lines_and_amount(move_values, previous_refund_moves, foreign_currency)
            current_refunded_lines = self._compute_refunded_lines_and_amount(move_values, current_refund_move, foreign_currency)
            return self._add_refund_info_to_tax_cash_basis_values(
                move_values=move_values,
                partial=partial,
                previous_payment_partials=previous_payment_partials,
                current_refunded_lines=current_refunded_lines,
                previous_refunded_lines=previous_refunded_lines,
                previous_excess_distribution_lines=previous_excess_distribution_lines,
                paid_percentage=paid_percentage,
                foreign_currency=foreign_currency,
                )

        return move_values

    def _collect_tax_cash_basis_values(self):
        ''' Collect all information needed to create the tax cash basis journal entries on the current partials.
        :return:    A dictionary mapping each move_id to the result of 'account_move._collect_tax_cash_basis_values'.
                    Also, add the 'partials' keys being a list of dictionary, one for each partial to process:
                        * partial:          The account.partial.reconcile record.
                        * percentage:       The reconciled percentage represented by the partial.
                        * payment_rate:     The applied rate of this partial.
        '''
        tax_cash_basis_values_per_move = {}

        if not self:
            return {}

        for partial in self:
            for move in {partial.debit_move_id.move_id, partial.credit_move_id.move_id}:

                # Collect data about cash basis.
                if move.id in tax_cash_basis_values_per_move:
                    move_values = tax_cash_basis_values_per_move[move.id]
                else:
                    move_values = move._collect_tax_cash_basis_values()

                # Nothing to process on the move.
                if not move_values:
                    continue

                # Check the cash basis configuration only when at least one cash basis tax entry need to be created.
                journal = partial.company_id.tax_cash_basis_journal_id

                if not journal:
                    raise UserError(_("There is no tax cash basis journal defined for the '%s' company.\n"
                                      "Configure it in Accounting/Configuration/Settings",
                                      partial.company_id.display_name))

                partial_amount = 0.0
                partial_amount_currency = 0.0
                rate_amount = 0.0
                rate_amount_currency = 0.0

                if partial.debit_move_id.move_id == move:
                    partial_amount += partial.amount
                    partial_amount_currency += partial.debit_amount_currency
                    rate_amount -= partial.credit_move_id.balance
                    rate_amount_currency -= partial.credit_move_id.amount_currency
                    source_line = partial.debit_move_id
                    counterpart_line = partial.credit_move_id

                if partial.credit_move_id.move_id == move:
                    partial_amount += partial.amount
                    partial_amount_currency += partial.credit_amount_currency
                    rate_amount += partial.debit_move_id.balance
                    rate_amount_currency += partial.debit_move_id.amount_currency
                    source_line = partial.credit_move_id
                    counterpart_line = partial.debit_move_id

                if move.move_type in ('out_invoice', 'in_invoice'):
                    move_values = self._update_tax_cash_basis_values(move_values, partial)

                if partial.debit_move_id.move_id.is_invoice(include_receipts=True) and partial.credit_move_id.move_id.is_invoice(include_receipts=True):
                    # Will match when reconciling a refund with an invoice.
                    # In this case, we want to use the rate of each businness document to compute its cash basis entry,
                    # not the rate of what it's reconciled with.
                    rate_amount = source_line.balance
                    rate_amount_currency = source_line.amount_currency
                    payment_date = move.date
                else:
                    payment_date = counterpart_line.date

                if move_values['currency'] == move.company_id.currency_id:
                    # Ignore the exchange difference.
                    if move.company_currency_id.is_zero(partial_amount):
                        continue

                    # Percentage made on company's currency.
                    percentage = partial_amount / move_values['total_balance']
                else:
                    # Ignore the exchange difference.
                    if move.currency_id.is_zero(partial_amount_currency):
                        continue

                    # Percentage made on foreign currency.
                    percentage = partial_amount_currency / move_values['total_amount_currency']

                if source_line.currency_id != counterpart_line.currency_id:
                    # When the invoice and the payment are not sharing the same foreign currency, the rate is computed
                    # on-the-fly using the payment date.
                    if 'forced_rate_from_register_payment' in self.env.context:
                        payment_rate = self.env.context['forced_rate_from_register_payment']
                    else:
                        payment_rate = self.env['res.currency']._get_conversion_rate(
                            counterpart_line.company_currency_id,
                            source_line.currency_id,
                            counterpart_line.company_id,
                            payment_date,
                        )
                elif rate_amount:
                    payment_rate = rate_amount_currency / rate_amount
                else:
                    payment_rate = 0.0

                tax_cash_basis_values_per_move[move.id] = move_values

                partial_vals = {
                    'partial': partial,
                    'percentage': percentage,
                    'payment_rate': payment_rate,
                    'both_move_posted': partial.debit_move_id.move_id.state == 'posted' and partial.credit_move_id.move_id.state == 'posted',
                }

                # Add partials.
                move_values.setdefault('partials', [])
                move_values['partials'].append(partial_vals)

        # Clean-up moves having nothing to process.
        return {k: v for k, v in tax_cash_basis_values_per_move.items() if v}

    @api.model
    def _prepare_cash_basis_base_line_vals(self, base_line, balance, amount_currency):
        ''' Prepare the values to be used to create the cash basis journal items for the tax base line
        passed as parameter.

        :param base_line:       An account.move.line being the base of some taxes.
        :param balance:         The balance to consider for this line.
        :param amount_currency: The balance in foreign currency to consider for this line.
        :return:                A python dictionary that could be passed to the create method of
                                account.move.line.
        '''
        account = base_line.company_id.account_cash_basis_base_account_id or base_line.account_id
        tax_ids = base_line.tax_ids.flatten_taxes_hierarchy().filtered(lambda x: x.tax_exigibility == 'on_payment')
        is_refund = base_line.is_refund
        tax_tags = tax_ids.get_tax_tags(is_refund, 'base')
        product_tags = base_line.tax_tag_ids.filtered(lambda x: x.applicability == 'products')
        all_tags = tax_tags + product_tags

        return {
            'name': base_line.move_id.name,
            'debit': balance if balance > 0.0 else 0.0,
            'credit': -balance if balance < 0.0 else 0.0,
            'amount_currency': amount_currency,
            'currency_id': base_line.currency_id.id,
            'partner_id': base_line.partner_id.id,
            'account_id': account.id,
            'tax_ids': [Command.set(tax_ids.ids)],
            'tax_tag_ids': [Command.set(all_tags.ids)],
            'analytic_distribution': base_line.analytic_distribution,
            'display_type': base_line.display_type,
        }

    @api.model
    def _prepare_cash_basis_counterpart_base_line_vals(self, cb_base_line_vals):
        ''' Prepare the move line used as a counterpart of the line created by
        _prepare_cash_basis_base_line_vals.

        :param cb_base_line_vals:   The line returned by _prepare_cash_basis_base_line_vals.
        :return:                    A python dictionary that could be passed to the create method of
                                    account.move.line.
        '''
        return {
            'name': cb_base_line_vals['name'],
            'debit': cb_base_line_vals['credit'],
            'credit': cb_base_line_vals['debit'],
            'account_id': cb_base_line_vals['account_id'],
            'amount_currency': -cb_base_line_vals['amount_currency'],
            'currency_id': cb_base_line_vals['currency_id'],
            'partner_id': cb_base_line_vals['partner_id'],
            'analytic_distribution': cb_base_line_vals['analytic_distribution'],
            'display_type': cb_base_line_vals['display_type'],
        }

    @api.model
    def _prepare_cash_basis_tax_line_vals(self, tax_line, balance, amount_currency):
        ''' Prepare the move line corresponding to a tax in the cash basis entry.

        :param tax_line:        An account.move.line record being a tax line.
        :param balance:         The balance to consider for this line.
        :param amount_currency: The balance in foreign currency to consider for this line.
        :return:                A python dictionary that could be passed to the create method of
                                account.move.line.
        '''
        tax_ids = tax_line.tax_ids.filtered(lambda x: x.tax_exigibility == 'on_payment')
        base_tags = tax_ids.get_tax_tags(tax_line.tax_repartition_line_id.filtered(lambda rl: rl.document_type == 'refund').tax_id, 'base')
        product_tags = tax_line.tax_tag_ids.filtered(lambda x: x.applicability == 'products')
        all_tags = base_tags + tax_line.tax_repartition_line_id.tag_ids + product_tags

        return {
            'name': tax_line.name,
            'debit': balance if balance > 0.0 else 0.0,
            'credit': -balance if balance < 0.0 else 0.0,
            'tax_base_amount': tax_line.tax_base_amount,
            'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
            'tax_ids': [Command.set(tax_ids.ids)],
            'tax_tag_ids': [Command.set(all_tags.ids)],
            'account_id': tax_line.tax_repartition_line_id.account_id.id or tax_line.company_id.account_cash_basis_base_account_id.id or tax_line.account_id.id,
            'amount_currency': amount_currency,
            'currency_id': tax_line.currency_id.id,
            'partner_id': tax_line.partner_id.id,
            'analytic_distribution': tax_line.analytic_distribution,
            'display_type': tax_line.display_type,
        }

    @api.model
    def _prepare_cash_basis_counterpart_tax_line_vals(self, tax_line, cb_tax_line_vals):
        ''' Prepare the move line used as a counterpart of the line created by
        _prepare_cash_basis_tax_line_vals.

        :param tax_line:            An account.move.line record being a tax line.
        :param cb_tax_line_vals:    The result of _prepare_cash_basis_counterpart_tax_line_vals.
        :return:                    A python dictionary that could be passed to the create method of
                                    account.move.line.
        '''
        return {
            'name': cb_tax_line_vals['name'],
            'debit': cb_tax_line_vals['credit'],
            'credit': cb_tax_line_vals['debit'],
            'account_id': tax_line.account_id.id,
            'amount_currency': -cb_tax_line_vals['amount_currency'],
            'currency_id': cb_tax_line_vals['currency_id'],
            'partner_id': cb_tax_line_vals['partner_id'],
            'analytic_distribution': cb_tax_line_vals['analytic_distribution'],
            'display_type': cb_tax_line_vals['display_type'],
        }

    @api.model
    def _get_cash_basis_base_line_grouping_key_from_vals(self, base_line_vals):
        ''' Get the grouping key of a cash basis base line that hasn't yet been created.
        :param base_line_vals:  The values to create a new account.move.line record.
        :return:                The grouping key as a tuple.
        '''
        tax_ids = base_line_vals['tax_ids'][0][2] # Decode [(6, 0, [...])] command
        base_taxes = self.env['account.tax'].browse(tax_ids)
        return (
            base_line_vals['currency_id'],
            base_line_vals['partner_id'],
            base_line_vals['account_id'],
            tuple(base_taxes.filtered(lambda x: x.tax_exigibility == 'on_payment').ids),
            frozendict(base_line_vals['analytic_distribution'] or {}),
        )

    @api.model
    def _get_cash_basis_tax_line_grouping_key_from_vals(self, tax_line_vals):
        ''' Get the grouping key of a cash basis tax line that hasn't yet been created.
        :param tax_line_vals:   The values to create a new account.move.line record.
        :return:                The grouping key as a tuple.
        '''
        tax_ids = tax_line_vals['tax_ids'][0][2] # Decode [(6, 0, [...])] command
        base_taxes = self.env['account.tax'].browse(tax_ids)
        return (
            tax_line_vals['currency_id'],
            tax_line_vals['partner_id'],
            tax_line_vals['account_id'],
            tuple(base_taxes.filtered(lambda x: x.tax_exigibility == 'on_payment').ids),
            tax_line_vals['tax_repartition_line_id'],
            frozendict(tax_line_vals['analytic_distribution'] or {}),
        )

    def _create_tax_cash_basis_moves(self):
        ''' Create the tax cash basis journal entries.
        :return: The newly created journal entries.
        '''
        tax_cash_basis_values_per_move = self._collect_tax_cash_basis_values()
        today = fields.Date.context_today(self)

        moves_to_create_and_post = []
        moves_to_create_in_draft = []
        to_reconcile_after = []
        payment_moves_to_recreate = []

        for move_values in tax_cash_basis_values_per_move.values():
            move = move_values['move']
            pending_cash_basis_lines = []
            amount_residual_per_tax_line = {
                line.id: line.amount_residual_currency for line_type, line, *line_amount in move_values['to_process_lines'] if line_type == 'tax'
            }

            if move_values.get('payment_moves_to_recreate', False):
                for payment_move in move_values['payment_moves_to_recreate']:
                    payment_moves_to_recreate.append(payment_move)

            for partial_values in move_values['partials']:
                partial = partial_values['partial']

                # Init the journal entry.
                journal = partial.company_id.tax_cash_basis_journal_id
                lock_date = move.company_id._get_user_fiscal_lock_date(journal)
                move_date = partial.max_date if partial.max_date > lock_date else today
                move_vals = {
                    'move_type': 'entry',
                    'date': move_date,
                    'ref': move.name,
                    'journal_id': journal.id,
                    'company_id': partial.company_id.id,
                    'line_ids': [],
                    'tax_cash_basis_rec_id': partial.id,
                    'tax_cash_basis_origin_move_id': move.id,
                    'fiscal_position_id': move.fiscal_position_id.id,
                }

                # Tracking of lines grouped all together.
                # Used to reduce the number of generated lines and to avoid rounding issues.
                partial_lines_to_create = {}

                for caba_treatment, line, *line_amount in move_values['to_process_lines']:
                    # ==========================================================================
                    # Compute the balance of the current line on the cash basis entry.
                    # This balance is a percentage representing the part of the journal entry
                    # that is actually paid by the current partial.
                    # ==========================================================================

                    if line_amount:
                        amount_currency = line_amount[0]
                    else:
                        # Percentage expressed in the foreign currency.
                        amount_currency = line.currency_id.round(line.amount_currency * partial_values['percentage'])

                    if (
                        caba_treatment == 'tax'
                        and (
                            move_values['is_fully_paid']
                            or line.currency_id.compare_amounts(abs(line.amount_residual_currency), abs(amount_currency)) < 0
                        )
                        and partial_values == move_values['partials'][-1]
                    ):
                        # If the move is supposed to be fully paid, and we're on the last partial for it,
                        # put the remaining amount to avoid rounding issues
                        amount_currency = amount_residual_per_tax_line[line.id]
                    if caba_treatment == 'tax':
                        amount_residual_per_tax_line[line.id] -= amount_currency
                    balance = partial_values['payment_rate'] and amount_currency / partial_values['payment_rate'] or 0.0

                    # ==========================================================================
                    # Prepare the mirror cash basis journal item of the current line.
                    # Group them all together as much as possible to reduce the number of
                    # generated journal items.
                    # Also track the computed balance in order to avoid rounding issues when
                    # the journal entry will be fully paid. At that case, we expect the exact
                    # amount of each line has been covered by the cash basis journal entries
                    # and well reported in the Tax Report.
                    # ==========================================================================

                    if caba_treatment == 'tax':
                        # Tax line.

                        cb_line_vals = self._prepare_cash_basis_tax_line_vals(line, balance, amount_currency)
                        grouping_key = self._get_cash_basis_tax_line_grouping_key_from_vals(cb_line_vals)
                    elif caba_treatment == 'base':
                        # Base line.

                        cb_line_vals = self._prepare_cash_basis_base_line_vals(line, balance, amount_currency)
                        grouping_key = self._get_cash_basis_base_line_grouping_key_from_vals(cb_line_vals)

                    if grouping_key in partial_lines_to_create:
                        aggregated_vals = partial_lines_to_create[grouping_key]['vals']

                        debit = aggregated_vals['debit'] + cb_line_vals['debit']
                        credit = aggregated_vals['credit'] + cb_line_vals['credit']
                        balance = debit - credit

                        aggregated_vals.update({
                            'debit': balance if balance > 0 else 0,
                            'credit': -balance if balance < 0 else 0,
                            'amount_currency': aggregated_vals['amount_currency'] + cb_line_vals['amount_currency'],
                        })

                        if caba_treatment == 'tax':
                            aggregated_vals.update({
                                'tax_base_amount': aggregated_vals['tax_base_amount'] + cb_line_vals['tax_base_amount'],
                            })
                            partial_lines_to_create[grouping_key]['tax_line'] += line
                    else:
                        partial_lines_to_create[grouping_key] = {
                            'vals': cb_line_vals,
                        }
                        if caba_treatment == 'tax':
                            partial_lines_to_create[grouping_key].update({
                                'tax_line': line,
                            })

                # ==========================================================================
                # Create the counterpart journal items.
                # ==========================================================================

                # To be able to retrieve the correct matching between the tax lines to reconcile
                # later, the lines will be created using a specific sequence.
                sequence = 0

                for grouping_key, aggregated_vals in partial_lines_to_create.items():
                    line_vals = aggregated_vals['vals']
                    line_vals['sequence'] = sequence

                    pending_cash_basis_lines.append((grouping_key, line_vals['amount_currency']))

                    if 'tax_repartition_line_id' in line_vals:
                        # Tax line.

                        tax_line = aggregated_vals['tax_line']
                        counterpart_line_vals = self._prepare_cash_basis_counterpart_tax_line_vals(tax_line, line_vals)
                        counterpart_line_vals['sequence'] = sequence + 1

                        if tax_line.account_id.reconcile:
                            move_index = len(moves_to_create_and_post) + len(moves_to_create_in_draft)
                            to_reconcile_after.append((tax_line, move_index, counterpart_line_vals['sequence']))

                    else:
                        # Base line.

                        counterpart_line_vals = self._prepare_cash_basis_counterpart_base_line_vals(line_vals)
                        counterpart_line_vals['sequence'] = sequence + 1

                    sequence += 2

                    move_vals['line_ids'] += [(0, 0, counterpart_line_vals), (0, 0, line_vals)]

                if partial_values['both_move_posted']:
                    moves_to_create_and_post.append(move_vals)
                else:
                    moves_to_create_in_draft.append(move_vals)

        moves = self.env['account.move'].with_context(
            skip_invoice_sync=True,
            skip_invoice_line_sync=True,
            skip_account_move_synchronization=True,
        ).create(moves_to_create_and_post + moves_to_create_in_draft)
        moves[:len(moves_to_create_and_post)]._post(soft=False)

        # Reconcile the tax lines being on a reconcile tax basis transfer account.
        reconciliation_plan = []
        exchange_account_per_move = self.env.context.get('exchange_account_per_move', {})
        for lines, move_index, sequence in to_reconcile_after:

            # In expenses, all move lines are created manually without any grouping on tax lines.
            # In that case, 'lines' could be already reconciled.
            lines = lines.filtered(lambda x: not x.reconciled)
            if not lines:
                continue

            counterpart_line = moves[move_index].line_ids.filtered(lambda line: line.sequence == sequence)

            # When dealing with tiny amounts, the line could have a zero amount and then, be already reconciled.
            if counterpart_line.reconciled:
                continue

            reconciliation_plan.append(counterpart_line + lines)
            exchange_account_per_move[moves[move_index]] = exchange_account_per_move.get(lines.move_id)

        # passing add_caba_vals in the context to make sure that any exchange diff that would be created for
        # this cash basis move would set the field draft_caba_move_vals accordingly on the partial
        self.env['account.move.line'].with_context(add_caba_vals=True)._reconcile_plan(reconciliation_plan)

        for payment_move in payment_moves_to_recreate:
            self._recreate_payment_moves(payment_move)

        return moves

    def _get_draft_caba_move_vals(self):
        self.ensure_one()
        debit_vals = self.debit_move_id.move_id._collect_tax_cash_basis_values() or {}
        credit_vals = self.credit_move_id.move_id._collect_tax_cash_basis_values() or {}
        if not debit_vals and not credit_vals:
            return False

        existing_draft_caba_move_vals = {}
        if self.draft_caba_move_vals:
            existing_draft_caba_move_vals = json.loads(self.draft_caba_move_vals)

        existing_draft_caba_move_vals.update({
            'debit_caba_lines': [(aml_type, aml.id) for aml_type, aml in debit_vals.get('to_process_lines', [])],
            'debit_total_balance': debit_vals.get('total_balance'),
            'debit_total_amount_currency': debit_vals.get('total_amount_currency'),
            'credit_caba_lines': [(aml_type, aml.id) for aml_type, aml in credit_vals.get('to_process_lines', [])],
            'credit_total_balance': credit_vals.get('total_balance'),
            'credit_total_amount_currency': credit_vals.get('total_amount_currency'),
        })
        return json.dumps(existing_draft_caba_move_vals)

    def _set_draft_caba_move_vals(self):
        for partial in self:
            partial.draft_caba_move_vals = partial._get_draft_caba_move_vals()
