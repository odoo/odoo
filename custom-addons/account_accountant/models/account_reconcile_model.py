from odoo import fields, models, Command, tools

import re
from collections import defaultdict
from dateutil.relativedelta import relativedelta


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    ####################################################
    # RECONCILIATION PROCESS
    ####################################################

    def _apply_lines_for_bank_widget(self, residual_amount_currency, partner, st_line):
        """ Apply the reconciliation model lines to the statement line passed as parameter.

        :param residual_amount_currency:    The open balance of the statement line in the bank reconciliation widget
                                            expressed in the statement line currency.
        :param partner:                     The partner set on the wizard.
        :param st_line:                     The statement line processed by the bank reconciliation widget.
        :return:                            A list of python dictionaries (one per reconcile model line) representing
                                            the journal items to be created by the current reconcile model.
        """
        self.ensure_one()
        currency = st_line.foreign_currency_id or st_line.journal_id.currency_id or st_line.company_currency_id
        if currency.is_zero(residual_amount_currency):
            return []

        vals_list = []
        for line in self.line_ids:
            vals = line._apply_in_bank_widget(residual_amount_currency, partner, st_line)
            amount_currency = vals['amount_currency']

            if currency.is_zero(amount_currency):
                continue

            vals_list.append(vals)
            residual_amount_currency -= amount_currency

        return vals_list

    def _get_taxes_move_lines_dict(self, tax, base_line_dict):
        ''' Get move.lines dict (to be passed to the create()) corresponding to a tax.
        :param tax:             An account.tax record.
        :param base_line_dict:  A dict representing the move.line containing the base amount.
        :return: A list of dict representing move.lines to be created corresponding to the tax.
        '''
        self.ensure_one()
        balance = base_line_dict['balance']

        tax_type = tax.type_tax_use
        is_refund = (tax_type == 'sale' and balance < 0) or (tax_type == 'purchase' and balance > 0)

        res = tax.compute_all(balance, is_refund=is_refund)

        new_aml_dicts = []
        for tax_res in res['taxes']:
            tax = self.env['account.tax'].browse(tax_res['id'])
            balance = tax_res['amount']
            name = ' '.join([x for x in [base_line_dict.get('name', ''), tax_res['name']] if x])
            new_aml_dicts.append({
                'account_id': tax_res['account_id'] or base_line_dict['account_id'],
                'journal_id': base_line_dict.get('journal_id', False),
                'name': name,
                'partner_id': base_line_dict.get('partner_id'),
                'balance': balance,
                'debit': balance > 0 and balance or 0,
                'credit': balance < 0 and -balance or 0,
                'analytic_distribution': tax.analytic and base_line_dict['analytic_distribution'],
                'tax_repartition_line_id': tax_res['tax_repartition_line_id'],
                'tax_ids': [(6, 0, tax_res['tax_ids'])],
                'tax_tag_ids': [(6, 0, tax_res['tag_ids'])],
                'group_tax_id': tax_res['group'].id if tax_res['group'] else False,
                'currency_id': False,
                'reconcile_model_id': self.id,
            })

            # Handle price included taxes.
            base_balance = tax_res['base']
            base_line_dict.update({
                'balance': base_balance,
                'debit': base_balance > 0 and base_balance or 0,
                'credit': base_balance < 0 and -base_balance or 0,
            })

        base_line_dict['tax_tag_ids'] = [(6, 0, res['base_tags'])]
        return new_aml_dicts

    def _get_write_off_move_lines_dict(self, residual_balance, partner_id):
        ''' Get move.lines dict corresponding to the reconciliation model's write-off lines.
        :param residual_balance:    The residual balance of the account on the manual reconciliation widget.
        :return: A list of dict representing move.lines to be created corresponding to the write-off lines.
        '''
        self.ensure_one()

        if self.rule_type == 'invoice_matching' and (not self.allow_payment_tolerance or self.payment_tolerance_param == 0):
            return []

        currency = self.company_id.currency_id

        lines_vals_list = []
        for line in self.line_ids:
            if line.amount_type == 'percentage':
                balance = currency.round(residual_balance * (line.amount / 100.0))
            elif line.amount_type == 'fixed':
                balance = currency.round(line.amount * (1 if residual_balance > 0.0 else -1))
            else:
                balance = 0.0

            if currency.is_zero(balance):
                continue

            writeoff_line = {
                'name': line.label,
                'balance': balance,
                'debit': balance > 0 and balance or 0,
                'credit': balance < 0 and -balance or 0,
                'account_id': line.account_id.id,
                'currency_id': currency.id,
                'analytic_distribution': line.analytic_distribution,
                'reconcile_model_id': self.id,
                'journal_id': line.journal_id.id,
                'tax_ids': [],
            }
            lines_vals_list.append(writeoff_line)

            residual_balance -= balance

            if line.tax_ids:
                taxes = line.tax_ids
                detected_fiscal_position = self.env['account.fiscal.position']._get_fiscal_position(self.env['res.partner'].browse(partner_id))
                if detected_fiscal_position:
                    taxes = detected_fiscal_position.map_tax(taxes)
                writeoff_line['tax_ids'] += [Command.set(taxes.ids)]
                # Multiple taxes with force_tax_included results in wrong computation, so we
                # only allow to set the force_tax_included field if we have one tax selected
                if line.force_tax_included:
                    taxes = taxes[0].with_context(force_price_include=True)
                tax_vals_list = self._get_taxes_move_lines_dict(taxes, writeoff_line)
                lines_vals_list += tax_vals_list
                if not line.force_tax_included:
                    for tax_line in tax_vals_list:
                        residual_balance -= tax_line['balance']

        return lines_vals_list

    ####################################################
    # RECONCILIATION CRITERIA
    ####################################################

    def _apply_rules(self, st_line, partner):
        ''' Apply criteria to get candidates for all reconciliation models.

        This function is called in enterprise by the reconciliation widget to match
        the statement line with the available candidates (using the reconciliation models).

        :param st_line: The statement line to match.
        :param partner: The partner to consider.
        :return:        A dict mapping each statement line id with:
            * aml_ids:          A list of account.move.line ids.
            * model:            An account.reconcile.model record (optional).
            * status:           'reconciled' if the lines has been already reconciled, 'write_off' if the write-off
                                must be applied on the statement line.
            * auto_reconcile:   A flag indicating if the match is enough significant to auto reconcile the candidates.
        '''
        available_models = self.filtered(lambda m: m.rule_type != 'writeoff_button').sorted()

        for rec_model in available_models:

            if not rec_model._is_applicable_for(st_line, partner):
                continue

            if rec_model.rule_type == 'invoice_matching':
                rules_map = rec_model._get_invoice_matching_rules_map()
                for rule_index in sorted(rules_map.keys()):
                    for rule_method in rules_map[rule_index]:
                        candidate_vals = rule_method(st_line, partner)
                        if not candidate_vals:
                            continue

                        if candidate_vals.get('amls'):
                            res = rec_model._get_invoice_matching_amls_result(st_line, partner, candidate_vals)
                            if res:
                                return {
                                    **res,
                                    'model': rec_model,
                                }
                        else:
                            return {
                                **candidate_vals,
                                'model': rec_model,
                            }

            elif rec_model.rule_type == 'writeoff_suggestion':
                return {
                    'model': rec_model,
                    'status': 'write_off',
                    'auto_reconcile': rec_model.auto_reconcile,
                }
        return {}

    def _is_applicable_for(self, st_line, partner):
        """ Returns true iff this reconciliation model can be used to search for matches
        for the provided statement line and partner.
        """
        self.ensure_one()

        # Filter on journals, amount nature, amount and partners
        # All the conditions defined in this block are non-match conditions.
        if ((self.match_journal_ids and st_line.move_id.journal_id not in self.match_journal_ids)
            or (self.match_nature == 'amount_received' and st_line.amount < 0)
            or (self.match_nature == 'amount_paid' and st_line.amount > 0)
            or (self.match_amount == 'lower' and abs(st_line.amount) >= self.match_amount_max)
            or (self.match_amount == 'greater' and abs(st_line.amount) <= self.match_amount_min)
            or (self.match_amount == 'between' and (abs(st_line.amount) > self.match_amount_max or abs(st_line.amount) < self.match_amount_min))
            or (self.match_partner and not partner)
            or (self.match_partner and self.match_partner_ids and partner not in self.match_partner_ids)
            or (self.match_partner and self.match_partner_category_ids and not (partner.category_id & self.match_partner_category_ids))
        ):
            return False

        # Filter on label, note and transaction_type
        for record, rule_field, record_field in [(st_line, 'label', 'payment_ref'), (st_line.move_id, 'note', 'narration'), (st_line, 'transaction_type', 'transaction_type')]:
            rule_term = (self['match_' + rule_field + '_param'] or '').lower()
            record_term = (record[record_field] or '').lower()

            # This defines non-match conditions
            if ((self['match_' + rule_field] == 'contains' and rule_term not in record_term)
                or (self['match_' + rule_field] == 'not_contains' and rule_term in record_term)
                or (self['match_' + rule_field] == 'match_regex' and not re.match(rule_term, record_term))
            ):
                return False

        return True

    def _get_invoice_matching_amls_domain(self, st_line, partner):
        aml_domain = st_line._get_default_amls_matching_domain()

        if st_line.amount > 0.0:
            aml_domain.append(('balance', '>', 0.0))
        else:
            aml_domain.append(('balance', '<', 0.0))

        currency = st_line.foreign_currency_id or st_line.currency_id
        if self.match_same_currency:
            aml_domain.append(('currency_id', '=', currency.id))

        if partner:
            aml_domain.append(('partner_id', '=', partner.id))

        if self.past_months_limit:
            date_limit = fields.Date.context_today(self) - relativedelta(months=self.past_months_limit)
            aml_domain.append(('date', '>=', fields.Date.to_string(date_limit)))

        return aml_domain

    def _get_st_line_text_values_for_matching(self, st_line):
        """ Collect the strings that could be used on the statement line to perform some matching.
        :param st_line: The current statement line.
        :return: A list of strings.
        """
        self.ensure_one()
        allowed_fields = []
        if self.match_text_location_label:
            allowed_fields.append('payment_ref')
        if self.match_text_location_note:
            allowed_fields.append('narration')
        if self.match_text_location_reference:
            allowed_fields.append('ref')
        return st_line._get_st_line_strings_for_matching(allowed_fields=allowed_fields)

    def _get_invoice_matching_st_line_tokens(self, st_line):
        """ Parse the textual information from the statement line passed as parameter
        in order to extract from it the meaningful information in order to perform the matching.

        :param st_line: A statement line.
        :return:    A tuple of list of tokens, each one being a string.
                    The first element is a list of tokens you may match on numerical information.
                    The second element is a list of tokens you may match exactly.
        """
        st_line_text_values = self._get_st_line_text_values_for_matching(st_line)
        significant_token_size = 4
        numerical_tokens = []
        exact_tokens = []
        text_tokens = []
        for text_value in st_line_text_values:
            tokens = [
                ''.join(x for x in token if re.match(r'[0-9a-zA-Z\s]', x))
                for token in (text_value or '').split()
            ]

            # Numerical tokens
            for token in tokens:
                # The token is too short to be significant.
                if len(token) < significant_token_size:
                    continue

                text_tokens.append(token)

                formatted_token = ''.join(x for x in token if x.isdecimal())

                # The token is too short after formatting to be significant.
                if len(formatted_token) < significant_token_size:
                    continue

                numerical_tokens.append(formatted_token)

            # Exact tokens.
            if len(tokens) == 1:
                exact_tokens.append(text_value)
        return numerical_tokens, exact_tokens, text_tokens

    def _get_invoice_matching_amls_candidates(self, st_line, partner):
        """ Returns the match candidates for the 'invoice_matching' rule, with respect to the provided parameters.

        :param st_line: A statement line.
        :param partner: The partner associated to the statement line.
        """
        def get_order_by_clause(alias=None):
            direction = 'DESC' if self.matching_order == 'new_first' else 'ASC'
            dotted_alias = f'{alias}.' if alias else ''
            return f'{dotted_alias}date_maturity {direction}, {dotted_alias}date {direction}, {dotted_alias}id {direction}'

        assert self.rule_type == 'invoice_matching'
        self.env['account.move'].flush_model()
        self.env['account.move.line'].flush_model()

        aml_domain = self._get_invoice_matching_amls_domain(st_line, partner)
        query = self.env['account.move.line']._where_calc(aml_domain)
        tables, where_clause, where_params = query.get_sql()

        aml_cte = ''
        all_params = []
        sub_queries = []
        numerical_tokens, exact_tokens, _text_tokens = self._get_invoice_matching_st_line_tokens(st_line)
        if numerical_tokens or exact_tokens:
            aml_cte = rf'''
                WITH aml_cte AS (
                    SELECT
                        account_move_line.id as account_move_line_id,
                        account_move_line.date as account_move_line_date,
                        account_move_line.date_maturity as account_move_line_date_maturity,
                        account_move_line.name as account_move_line_name,
                        account_move_line__move_id.name as account_move_line__move_id_name,
                        account_move_line__move_id.ref as account_move_line__move_id_ref
                    FROM {tables}
                    JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
                    WHERE {where_clause}
                )
            '''
            all_params += where_params
        if numerical_tokens:
            for table_alias, field in (
                ('account_move_line', 'name'),
                ('account_move_line__move_id', 'name'),
                ('account_move_line__move_id', 'ref'),
            ):
                sub_queries.append(rf'''
                    SELECT
                        account_move_line_id as id,
                        account_move_line_date as date,
                        account_move_line_date_maturity as date_maturity,
                        UNNEST(
                            REGEXP_SPLIT_TO_ARRAY(
                                SUBSTRING(
                                    REGEXP_REPLACE({table_alias}_{field}, '[^0-9\s]', '', 'g'),
                                    '\S(?:.*\S)*'
                                ),
                                '\s+'
                            )
                        ) AS token
                    FROM aml_cte
                    WHERE {table_alias}_{field} IS NOT NULL
                ''')
        if exact_tokens:
            for table_alias, field in (
                ('account_move_line', 'name'),
                ('account_move_line__move_id', 'name'),
                ('account_move_line__move_id', 'ref'),
            ):
                sub_queries.append(rf'''
                    SELECT
                        account_move_line_id as id,
                        account_move_line_date as date,
                        account_move_line_date_maturity as date_maturity,
                        {table_alias}_{field} AS token
                    FROM aml_cte
                    WHERE COALESCE({table_alias}_{field}, '') != ''
                ''')
        if sub_queries:
            order_by = get_order_by_clause(alias='sub')
            self._cr.execute(
                aml_cte +
                '''
                    SELECT
                        sub.id,
                        COUNT(*) AS nb_match
                    FROM (''' + ' UNION ALL '.join(sub_queries) + ''') AS sub
                    WHERE sub.token IN %s
                    GROUP BY sub.date_maturity, sub.date, sub.id
                    HAVING COUNT(*) > 0
                    ORDER BY nb_match DESC, ''' + order_by + '''
                ''',
                all_params + [tuple(numerical_tokens + exact_tokens)],
            )
            candidate_ids = [r[0] for r in self._cr.fetchall()]
            if candidate_ids:
                return {
                    'allow_auto_reconcile': True,
                    'amls': self.env['account.move.line'].browse(candidate_ids),
                }

        if not partner:
            st_line_currency = st_line.foreign_currency_id or st_line.journal_id.currency_id or st_line.company_currency_id
            if st_line_currency == self.company_id.currency_id:
                aml_amount_field = 'amount_residual'
            else:
                aml_amount_field = 'amount_residual_currency'

            order_by = get_order_by_clause(alias='account_move_line')
            self._cr.execute(
                f'''
                    SELECT account_move_line.id
                    FROM {tables}
                    WHERE
                        {where_clause}
                        AND account_move_line.currency_id = %s
                        AND ROUND(account_move_line.{aml_amount_field}, %s) = ROUND(%s, %s)
                    ORDER BY {order_by}
                ''',
                where_params + [
                    st_line_currency.id,
                    st_line_currency.decimal_places,
                    -st_line.amount_residual,
                    st_line_currency.decimal_places,
                ],
            )
            amls = self.env['account.move.line'].browse([row[0] for row in self._cr.fetchall()])
        else:
            amls = self.env['account.move.line'].search(aml_domain, order=get_order_by_clause())

        if amls:
            return {
                'allow_auto_reconcile': False,
                'amls': amls,
            }

    def _get_invoice_matching_rules_map(self):
        """ Get a mapping <priority_order, rule> that could be overridden in others modules.

        :return: a mapping <priority_order, rule> where:
            * priority_order:   Defines in which order the rules will be evaluated, the lowest comes first.
                                This is extremely important since the algorithm stops when a rule returns some candidates.
            * rule:             Method taking <st_line, partner> as parameters and returning the candidates journal items found.
        """
        rules_map = defaultdict(list)
        rules_map[10].append(self._get_invoice_matching_amls_candidates)
        return rules_map

    def _get_partner_from_mapping(self, st_line):
        """Find partner with mapping defined on model.

        For invoice matching rules, matches the statement line against each
        regex defined in partner mapping, and returns the partner corresponding
        to the first one matching.

        :param st_line (Model<account.bank.statement.line>):
            The statement line that needs a partner to be found
        :return Model<res.partner>:
            The partner found from the mapping. Can be empty an empty recordset
            if there was nothing found from the mapping or if the function is
            not applicable.
        """
        self.ensure_one()

        if self.rule_type not in ('invoice_matching', 'writeoff_suggestion'):
            return self.env['res.partner']

        for partner_mapping in self.partner_mapping_line_ids:
            match_payment_ref = True
            if partner_mapping.payment_ref_regex:
                match_payment_ref = re.match(partner_mapping.payment_ref_regex, st_line.payment_ref) if st_line.payment_ref else False

            match_narration = True
            if partner_mapping.narration_regex:
                match_narration = re.match(
                    partner_mapping.narration_regex,
                    tools.html2plaintext(st_line.narration or '').rstrip(),
                    flags=re.DOTALL, # Ignore '/n' set by online sync.
                )

            if match_payment_ref and match_narration:
                return partner_mapping.partner_id
        return self.env['res.partner']

    def _get_invoice_matching_amls_result(self, st_line, partner, candidate_vals):
        def _create_result_dict(amls_values_list, status):
            if 'rejected' in status:
                return

            result = {'amls': self.env['account.move.line']}
            for aml_values in amls_values_list:
                result['amls'] |= aml_values['aml']

            if 'allow_write_off' in status and self.line_ids:
                result['status'] = 'write_off'

            if 'allow_auto_reconcile' in status and candidate_vals['allow_auto_reconcile'] and self.auto_reconcile:
                result['auto_reconcile'] = True

            return result

        st_line_currency = st_line.foreign_currency_id or st_line.currency_id
        st_line_amount = st_line._prepare_move_line_default_vals()[1]['amount_currency']
        sign = 1 if st_line_amount > 0.0 else -1

        amls = candidate_vals['amls']
        amls_values_list = []
        amls_with_epd_values_list = []
        same_currency_mode = amls.currency_id == st_line_currency
        for aml in amls:
            aml_values = {
                'aml': aml,
                'amount_residual': aml.amount_residual,
                'amount_residual_currency': aml.amount_residual_currency,
            }

            amls_values_list.append(aml_values)

            # Manage the early payment discount.
            if aml.move_id.invoice_payment_term_id:
                last_discount_date = aml.move_id.invoice_payment_term_id._get_last_discount_date(aml.move_id.date)
            else:
                last_discount_date = False
            if same_currency_mode \
                    and aml.move_id.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt') \
                    and not aml.matched_debit_ids \
                    and not aml.matched_credit_ids \
                    and last_discount_date \
                    and st_line.date <= last_discount_date:

                rate = abs(aml.amount_currency) / abs(aml.balance) if aml.balance else 1.0
                amls_with_epd_values_list.append({
                    **aml_values,
                    'amount_residual': st_line.company_currency_id.round(aml.discount_amount_currency / rate),
                    'amount_residual_currency': aml.discount_amount_currency,
                })
            else:
                amls_with_epd_values_list.append(aml_values)

        def match_batch_amls(amls_values_list):
            if not same_currency_mode:
                return None, []

            kepts_amls_values_list = []
            sum_amount_residual_currency = 0.0
            for aml_values in amls_values_list:

                if st_line_currency.compare_amounts(st_line_amount, -aml_values['amount_residual_currency']) == 0:
                    # Special case: the amounts are the same, submit the line directly.
                    return 'perfect', [aml_values]

                if st_line_currency.compare_amounts(sign * (st_line_amount + sum_amount_residual_currency), 0.0) > 0:
                    # Here, we still have room for other candidates ; so we add the current one to the list we keep.
                    # Then, we continue iterating, even if there is no room anymore, just in case one of the following candidates
                    # is an exact match, which would then be preferred on the current candidates.
                    kepts_amls_values_list.append(aml_values)
                    sum_amount_residual_currency += aml_values['amount_residual_currency']

            if st_line_currency.is_zero(sign * (st_line_amount + sum_amount_residual_currency)):
                return 'perfect', kepts_amls_values_list
            elif kepts_amls_values_list:
                return 'partial', kepts_amls_values_list
            else:
                return None, []

        # Try to match a batch with the early payment feature. Only a perfect match is allowed.
        match_type, kepts_amls_values_list = match_batch_amls(amls_with_epd_values_list)
        if match_type != 'perfect':
            kepts_amls_values_list = []

        # Try to match the amls having the same currency as the statement line.
        if not kepts_amls_values_list:
            _match_type, kepts_amls_values_list = match_batch_amls(amls_values_list)

        # Try to match the whole candidates.
        if not kepts_amls_values_list:
            kepts_amls_values_list = amls_values_list

        # Try to match the amls having the same currency as the statement line.
        if kepts_amls_values_list:
            status = self._check_rule_propositions(st_line, kepts_amls_values_list)
            result = _create_result_dict(kepts_amls_values_list, status)
            if result:
                return result

    def _check_rule_propositions(self, st_line, amls_values_list):
        """ Check restrictions that can't be handled for each move.line separately.
        Note: Only used by models having a type equals to 'invoice_matching'.
        :param st_line:             The statement line.
        :param amls_values_list:    The candidates account.move.line as a list of dict:
            * aml:                          The record.
            * amount_residual:              The amount residual to consider.
            * amount_residual_currency:     The amount residual in foreign currency to consider.
        :return: A string representing what to do with the candidates:
            * rejected:             Reject candidates.
            * allow_write_off:      Allow to generate the write-off from the reconcile model lines if specified.
            * allow_auto_reconcile: Allow to automatically reconcile entries if 'auto_validate' is enabled.
        """
        self.ensure_one()

        if not self.allow_payment_tolerance:
            return {'allow_write_off', 'allow_auto_reconcile'}

        st_line_currency = st_line.foreign_currency_id or st_line.currency_id
        st_line_amount_curr = st_line._prepare_move_line_default_vals()[1]['amount_currency']
        amls_amount_curr = sum(
            st_line._prepare_counterpart_amounts_using_st_line_rate(
                aml_values['aml'].currency_id,
                aml_values['amount_residual'],
                aml_values['amount_residual_currency'],
            )['amount_currency']
            for aml_values in amls_values_list
        )
        sign = 1 if st_line_amount_curr > 0.0 else -1
        amount_curr_after_rec = st_line_currency.round(
            sign * (amls_amount_curr + st_line_amount_curr)
        )

        # The statement line will be fully reconciled.
        if st_line_currency.is_zero(amount_curr_after_rec):
            return {'allow_auto_reconcile'}

        # The payment amount is higher than the sum of invoices.
        # In that case, don't check the tolerance and don't try to generate any write-off.
        if amount_curr_after_rec > 0.0:
            return {'allow_auto_reconcile'}

        # No tolerance, reject the candidates.
        if self.payment_tolerance_param == 0:
            return {'rejected'}

        # If the tolerance is expressed as a fixed amount, check the residual payment amount doesn't exceed the
        # tolerance.
        if self.payment_tolerance_type == 'fixed_amount' and st_line_currency.compare_amounts(-amount_curr_after_rec, self.payment_tolerance_param) <= 0:
            return {'allow_write_off', 'allow_auto_reconcile'}

        # The tolerance is expressed as a percentage between 0 and 100.0.
        reconciled_percentage_left = (abs(amount_curr_after_rec / amls_amount_curr)) * 100.0
        if self.payment_tolerance_type == 'percentage' and st_line_currency.compare_amounts(reconciled_percentage_left, self.payment_tolerance_param) <= 0:
            return {'allow_write_off', 'allow_auto_reconcile'}

        return {'rejected'}

    def run_auto_reconciliation(self):
        """ Tries to auto-reconcile as many statements as possible within time limit
        arbitrary set to 3 minutes (the rest will be reconciled asynchronously with the regular cron).
        """
        # 'limit_time_real_cron' defaults to -1.
        # Manual fallback applied for non-POSIX systems where this key is disabled (set to None).
        cron_limit_time = tools.config['limit_time_real_cron'] or -1
        limit_time = cron_limit_time if 0 < cron_limit_time < 180 else 180
        self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines(limit_time=limit_time)
