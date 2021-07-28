# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import date


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Reconcile"
    _rec_name = "id"

    # ==== Reconciliation fields ====
    debit_move_id = fields.Many2one(
        comodel_name='account.move.line',
        index=True, required=True)
    credit_move_id = fields.Many2one(
        comodel_name='account.move.line',
        index=True, required=True)
    full_reconcile_id = fields.Many2one(
        comodel_name='account.full.reconcile',
        string="Full Reconcile", copy=False)

    # ==== Currency fields ====
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Company Currency",
        related='company_id.currency_id',
        help="Utility field to express amount currency")
    debit_currency_id = fields.Many2one(
        comodel_name='res.currency',
        store=True,
        compute='_compute_debit_currency_id',
        string="Currency of the debit journal item.")
    credit_currency_id = fields.Many2one(
        comodel_name='res.currency',
        store=True,
        compute='_compute_credit_currency_id',
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
        related='debit_move_id.company_id')
    max_date = fields.Date(
        string="Max Date of Matched Lines", store=True,
        compute='_compute_max_date',
        help="Technical field used to determine at which date this reconciliation needs to be shown on the "
             "aged receivable/payable reports.")

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

    @api.depends('debit_move_id')
    def _compute_debit_currency_id(self):
        for partial in self:
            partial.debit_currency_id = partial.debit_move_id.currency_id \
                                        or partial.debit_move_id.company_currency_id

    @api.depends('credit_move_id')
    def _compute_credit_currency_id(self):
        for partial in self:
            partial.credit_currency_id = partial.credit_move_id.currency_id \
                                        or partial.credit_move_id.company_currency_id

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

        # Retrieve the matching number to unlink.
        full_to_unlink = self.full_reconcile_id

        # Retrieve the CABA entries to reverse.
        moves_to_reverse = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self.ids)])

        # Unlink partials before doing anything else to avoid 'Record has already been deleted' due to the recursion.
        res = super().unlink()

        # Reverse CABA entries.
        today = fields.Date.context_today(self)
        default_values_list = [{
            'date': move.date if move.date > (move.company_id.period_lock_date or date.min) else today,
            'ref': _('Reversal of: %s') % move.name,
        } for move in moves_to_reverse]
        moves_to_reverse._reverse_moves(default_values_list, cancel=True)

        # Remove the matching numbers.
        full_to_unlink.unlink()

        return res

    # -------------------------------------------------------------------------
    # RECONCILIATION METHODS
    # -------------------------------------------------------------------------

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
                if move.id not in tax_cash_basis_values_per_move:
                    tax_cash_basis_values_per_move[move.id] = move._collect_tax_cash_basis_values()

                # Nothing to process on the move.
                if not tax_cash_basis_values_per_move.get(move.id):
                    continue
                move_values = tax_cash_basis_values_per_move[move.id]

                # Check the cash basis configuration only when at least one cash basis tax entry need to be created.
                journal = partial.company_id.tax_cash_basis_journal_id

                if not journal:
                    raise UserError(_("There is no tax cash basis journal defined for the '%s' company.\n"
                                      "Configure it in Accounting/Configuration/Settings") % partial.company_id.display_name)

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

                if move_values['currency'] == move.company_id.currency_id:
                    # Percentage made on company's currency.
                    percentage = partial_amount / move_values['total_balance']
                else:
                    # Percentage made on foreign currency.
                    percentage = partial_amount_currency / move_values['total_amount_currency']

                if source_line.currency_id != counterpart_line.currency_id:
                    # When the invoice and the payment are not sharing the same foreign currency, the rate is computed
                    # on-the-fly using the payment date.
                    payment_rate = self.env['res.currency']._get_conversion_rate(
                        counterpart_line.company_currency_id,
                        source_line.currency_id,
                        counterpart_line.company_id,
                        counterpart_line.date,
                    )
                elif rate_amount:
                    payment_rate = rate_amount_currency / rate_amount
                else:
                    payment_rate = 0.0

                partial_vals = {
                    'partial': partial,
                    'percentage': percentage,
                    'payment_rate': payment_rate,
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
        return {
            'name': base_line.move_id.name,
            'debit': balance if balance > 0.0 else 0.0,
            'credit': -balance if balance < 0.0 else 0.0,
            'amount_currency': amount_currency,
            'currency_id': base_line.currency_id.id,
            'partner_id': base_line.partner_id.id,
            'account_id': account.id,
            'tax_ids': [(6, 0, base_line.tax_ids.ids)],
            'tax_tag_ids': [(6, 0, base_line._convert_tags_for_cash_basis(base_line.tax_tag_ids).ids)],
            'tax_exigible': True,
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
            'tax_exigible': True,
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
        return {
            'name': tax_line.name,
            'debit': balance if balance > 0.0 else 0.0,
            'credit': -balance if balance < 0.0 else 0.0,
            'tax_base_amount': tax_line.tax_base_amount,
            'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
            'tax_ids': [(6, 0, tax_line.tax_ids.ids)],
            'tax_tag_ids': [(6, 0, tax_line._convert_tags_for_cash_basis(tax_line.tax_tag_ids).ids)],
            'account_id': tax_line.tax_repartition_line_id.account_id.id or tax_line.account_id.id,
            'amount_currency': amount_currency,
            'currency_id': tax_line.currency_id.id,
            'partner_id': tax_line.partner_id.id,
            'tax_exigible': True,
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
            'tax_exigible': True,
        }

    @api.model
    def _get_cash_basis_base_line_grouping_key_from_vals(self, base_line_vals):
        ''' Get the grouping key of a cash basis base line that hasn't yet been created.
        :param base_line_vals:  The values to create a new account.move.line record.
        :return:                The grouping key as a tuple.
        '''
        return (
            base_line_vals['currency_id'],
            base_line_vals['partner_id'],
            base_line_vals['account_id'],
            tuple(base_line_vals['tax_ids'][0][2]),     # Decode [(6, 0, [...])] command
            tuple(base_line_vals['tax_tag_ids'][0][2]), # Decode [(6, 0, [...])] command
        )

    @api.model
    def _get_cash_basis_base_line_grouping_key_from_record(self, base_line, account=None):
        ''' Get the grouping key of a journal item being a base line.
        :param base_line:   An account.move.line record.
        :param account:     Optional account to shadow the current base_line one.
        :return:            The grouping key as a tuple.
        '''
        return (
            base_line.currency_id.id,
            base_line.partner_id.id,
            (account or base_line.account_id).id,
            tuple(base_line.tax_ids.ids),
            tuple(base_line._convert_tags_for_cash_basis(base_line.tax_tag_ids).ids),
        )

    @api.model
    def _get_cash_basis_tax_line_grouping_key_from_vals(self, tax_line_vals):
        ''' Get the grouping key of a cash basis tax line that hasn't yet been created.
        :param tax_line_vals:   The values to create a new account.move.line record.
        :return:                The grouping key as a tuple.
        '''
        return (
            tax_line_vals['currency_id'],
            tax_line_vals['partner_id'],
            tax_line_vals['account_id'],
            tuple(tax_line_vals['tax_ids'][0][2]),      # Decode [(6, 0, [...])] command
            tuple(tax_line_vals['tax_tag_ids'][0][2]),  # Decode [(6, 0, [...])] command
            tax_line_vals['tax_repartition_line_id'],
        )

    @api.model
    def _get_cash_basis_tax_line_grouping_key_from_record(self, tax_line, account=None):
        ''' Get the grouping key of a journal item being a tax line.
        :param tax_line:    An account.move.line record.
        :param account:     Optional account to shadow the current tax_line one.
        :return:            The grouping key as a tuple.
        '''
        return (
            tax_line.currency_id.id,
            tax_line.partner_id.id,
            (account or tax_line.account_id).id,
            tuple(tax_line.tax_ids.ids),
            tuple(tax_line._convert_tags_for_cash_basis(tax_line.tax_tag_ids).ids),
            tax_line.tax_repartition_line_id.id,
        )

    @api.model
    def _fix_cash_basis_full_balance_coverage(self, move_values, partial_values, pending_cash_basis_lines, partial_lines_to_create):
        ''' This method is used to ensure the full coverage of the current move when it becomes fully paid.
        For example, suppose a line of 0.03 paid 50-50. Without this method, each cash basis entry will report
        0.03 / 0.5 = 0.015 ~ 0.02 per cash entry on the tax report as base amount, for a total of 0.04.
        This is wrong because we expect 0.03.on the tax report as base amount. This is wrong because we expect 0.03.

        :param move_values:                 The collected values about cash basis for the current move.
        :param partial_values:              The collected values about cash basis for the current partial.
        :param pending_cash_basis_lines:    The previously generated lines during this reconciliation but not yet created.
        :param partial_lines_to_create:     The generated lines for the current and last partial making the move fully paid.
        '''
        # DEPRECATED: TO BE REMOVED IN MASTER
        residual_amount_per_group = {}
        move = move_values['move']

        # ==========================================================================
        # Part 1:
        # Add the balance of all journal items that are not tax exigible in order to
        # ensure the exact balance will be report on the Tax Report.
        # This part is needed when the move will be fully paid after the current
        # reconciliation.
        # ==========================================================================

        for line in move_values['to_process_lines']:
            if line.tax_repartition_line_id:
                # Tax line.
                grouping_key = self._get_cash_basis_tax_line_grouping_key_from_record(
                    line,
                    account=line.tax_repartition_line_id.account_id,
                )
                residual_amount_per_group.setdefault(grouping_key, 0.0)
                residual_amount_per_group[grouping_key] += line['amount_currency']

            elif line.tax_ids:
                # Base line.
                grouping_key = self._get_cash_basis_base_line_grouping_key_from_record(
                    line,
                    account=line.company_id.account_cash_basis_base_account_id,
                )
                residual_amount_per_group.setdefault(grouping_key, 0.0)
                residual_amount_per_group[grouping_key] += line['amount_currency']

        # ==========================================================================
        # Part 2:
        # Subtract all previously created cash basis journal items during previous
        # reconciliation.
        # ==========================================================================

        previous_tax_cash_basis_moves = self.env['account.move'].search([
            '|',
            ('tax_cash_basis_rec_id', 'in', self.ids),
            ('tax_cash_basis_move_id', '=', move.id),
        ])
        for line in previous_tax_cash_basis_moves.line_ids:
            if line.tax_repartition_line_id:
                # Tax line.
                grouping_key = self._get_cash_basis_tax_line_grouping_key_from_record(line)
            elif line.tax_ids:
                # Base line.
                grouping_key = self._get_cash_basis_base_line_grouping_key_from_record(line)
            else:
                continue

            if grouping_key not in residual_amount_per_group:
                # The grouping_key is unknown regarding the current lines.
                # Maybe this move has been created before migration and then,
                # we are not able to ensure the full coverage of the balance.
                return

            residual_amount_per_group[grouping_key] -= line['amount_currency']

        # ==========================================================================
        # Part 3:
        # Subtract all pending cash basis journal items that will be created during
        # this reconciliation.
        # ==========================================================================

        for grouping_key, balance in pending_cash_basis_lines:
            residual_amount_per_group[grouping_key] -= balance

        # ==========================================================================
        # Part 4:
        # Fix the current cash basis journal items in progress by replacing the
        # balance by the residual one.
        # ==========================================================================

        for grouping_key, aggregated_vals in partial_lines_to_create.items():
            line_vals = aggregated_vals['vals']

            amount_currency = residual_amount_per_group[grouping_key]
            balance = partial_values['payment_rate'] and amount_currency / partial_values['payment_rate'] or 0.0
            line_vals.update({
                'debit': balance if balance > 0.0 else 0.0,
                'credit': -balance if balance < 0.0 else 0.0,
                'amount_currency': amount_currency,
            })

    def _create_tax_cash_basis_moves(self):
        ''' Create the tax cash basis journal entries.
        :return: The newly created journal entries.
        '''
        tax_cash_basis_values_per_move = self._collect_tax_cash_basis_values()

        moves_to_create = []
        to_reconcile_after = []
        for move_values in tax_cash_basis_values_per_move.values():
            move = move_values['move']
            pending_cash_basis_lines = []

            for partial_values in move_values['partials']:
                partial = partial_values['partial']

                # Init the journal entry.
                move_vals = {
                    'move_type': 'entry',
                    'date': partial.max_date,
                    'ref': move.name,
                    'journal_id': partial.company_id.tax_cash_basis_journal_id.id,
                    'line_ids': [],
                    'tax_cash_basis_rec_id': partial.id,
                    'tax_cash_basis_move_id': move.id,
                }

                # Tracking of lines grouped all together.
                # Used to reduce the number of generated lines and to avoid rounding issues.
                partial_lines_to_create = {}

                for line in move_values['to_process_lines']:

                    # ==========================================================================
                    # Compute the balance of the current line on the cash basis entry.
                    # This balance is a percentage representing the part of the journal entry
                    # that is actually paid by the current partial.
                    # ==========================================================================

                    # Percentage expressed in the foreign currency.
                    amount_currency = line.currency_id.round(line.amount_currency * partial_values['percentage'])
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

                    if line.tax_repartition_line_id:
                        # Tax line.

                        cb_line_vals = self._prepare_cash_basis_tax_line_vals(line, balance, amount_currency)
                        grouping_key = self._get_cash_basis_tax_line_grouping_key_from_vals(cb_line_vals)
                    elif line.tax_ids:
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

                        if line.tax_repartition_line_id:
                            aggregated_vals.update({
                                'tax_base_amount': aggregated_vals['tax_base_amount'] + cb_line_vals['tax_base_amount'],
                            })
                            partial_lines_to_create[grouping_key]['tax_line'] += line
                    else:
                        partial_lines_to_create[grouping_key] = {
                            'vals': cb_line_vals,
                        }
                        if line.tax_repartition_line_id:
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
                            move_index = len(moves_to_create)
                            to_reconcile_after.append((tax_line, move_index, counterpart_line_vals['sequence']))

                    else:
                        # Base line.

                        counterpart_line_vals = self._prepare_cash_basis_counterpart_base_line_vals(line_vals)
                        counterpart_line_vals['sequence'] = sequence + 1

                    sequence += 2

                    move_vals['line_ids'] += [(0, 0, counterpart_line_vals), (0, 0, line_vals)]

                moves_to_create.append(move_vals)

        moves = self.env['account.move'].create(moves_to_create)
        moves._post(soft=False)

        # Reconcile the tax lines being on a reconcile tax basis transfer account.
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

            (lines + counterpart_line).reconcile()

        return moves
