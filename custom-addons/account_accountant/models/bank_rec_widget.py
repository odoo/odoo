# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
import json
import markupsafe

from odoo import _, api, fields, models, Command
from odoo.addons.web.controllers.utils import clean_action
from odoo.tools.misc import formatLang


class BankRecWidget(models.Model):
    _name = "bank.rec.widget"
    _description = "Bank reconciliation widget for a single statement line"

    # This model is never saved inside the database.
    # _auto=False' & _table_query = "0" prevent the ORM to create the corresponding postgresql table.
    _auto = False
    _table_query = "0"

    # ==== Business fields ====
    st_line_id = fields.Many2one(comodel_name='account.bank.statement.line')
    move_id = fields.Many2one(
        related='st_line_id.move_id',
        depends=['st_line_id'],
    )
    st_line_to_check = fields.Boolean(
        related='st_line_id.move_id.to_check',
        depends=['st_line_id'],
    )
    st_line_is_reconciled = fields.Boolean(
        related='st_line_id.is_reconciled',
        depends=['st_line_id'],
    )
    st_line_journal_id = fields.Many2one(
        related='st_line_id.journal_id',
        depends=['st_line_id'],
    )
    st_line_narration = fields.Html(  # FIXME remove in master. Deprecated field, use st_line_transaction_details instead
        related='st_line_id.narration',
        depends=['st_line_id'],
    )
    st_line_transaction_details = fields.Html(
        compute='_compute_st_line_transaction_details',
    )
    transaction_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_transaction_currency_id',
    )
    journal_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_journal_currency_id',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        compute='_compute_partner_id',
        store=True,
        readonly=False,
    )
    line_ids = fields.One2many(
        comodel_name='bank.rec.widget.line',
        inverse_name='wizard_id',
        compute='_compute_line_ids',
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    available_reco_model_ids = fields.Many2many(
        comodel_name='account.reconcile.model',
        compute='_compute_available_reco_model_ids',
        store=True,
        readonly=False,
    )
    selected_reco_model_id = fields.Many2one(
        comodel_name='account.reconcile.model',
        compute='_compute_selected_reco_model_id',
    )
    partner_name = fields.Char(
        related='st_line_id.partner_name',
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        related='st_line_id.company_id',
        depends=['st_line_id'],
    )
    company_currency_id = fields.Many2one(
        string="Wizard Company Currency",
        related='company_id.currency_id',
        depends=['st_line_id'],
    )
    matching_rules_allow_auto_reconcile = fields.Boolean()

    # ==== Display fields ====
    state = fields.Selection(
        selection=[
            ('invalid', "Invalid"),
            ('valid', "Valid"),
            ('reconciled', "Reconciled"),
        ],
        compute='_compute_state',
        store=True,
        help="Invalid: The bank transaction can't be validate since the suspense account is still involved\n"
             "Valid: The bank transaction can be validated.\n"
             "Reconciled: The bank transaction has already been processed. Nothing left to do."
    )

    # ==== JS fields ====
    selected_aml_ids = fields.Many2many(
        comodel_name='account.move.line',
        compute='_compute_selected_aml_ids',
    )
    todo_command = fields.Json(
        store=False,
    )
    return_todo_command = fields.Json(
        store=False,
    )
    form_index = fields.Char()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('st_line_id')
    def _compute_line_ids(self):
        for wizard in self:
            if wizard.st_line_id:

                is_reconciled = wizard.st_line_id.is_reconciled

                # Liquidity line.
                line_ids_commands = [
                    Command.clear(),
                    Command.create(wizard._lines_prepare_liquidity_line()),
                ]

                # Existing amls if the statement line is already reconciled.
                if is_reconciled:
                    _liquidity_lines, _suspense_lines, other_lines = wizard.st_line_id._seek_for_lines()
                    for aml in other_lines:
                        exchange_diff_amls = (aml.matched_debit_ids + aml.matched_credit_ids) \
                            .exchange_move_id.line_ids.filtered(lambda l: l.account_id != aml.account_id)
                        if wizard.state == 'reconciled' and exchange_diff_amls:
                            line_ids_commands.append(
                                Command.create(wizard._lines_prepare_aml_line(
                                    aml,  # Create the aml line with un-squashed amounts (aml - exchange diff)
                                    balance=aml.balance - sum(exchange_diff_amls.mapped('balance')),
                                    amount_currency=aml.amount_currency - sum(exchange_diff_amls.mapped('amount_currency')),
                                ))
                            )
                            for exchange_diff_aml in exchange_diff_amls:
                                line_ids_commands.append(
                                    Command.create(wizard._lines_prepare_aml_line(exchange_diff_aml))
                                )
                        else:
                            line_ids_commands.append(Command.create(wizard._lines_prepare_aml_line(aml)))

                wizard.line_ids = line_ids_commands

                wizard._lines_add_auto_balance_line()

            else:

                wizard.line_ids = [Command.clear()]

    @api.depends('st_line_id')
    def _compute_available_reco_model_ids(self):
        for wizard in self:
            if wizard.st_line_id:
                available_reco_models = self.env['account.reconcile.model'].search([
                    ('rule_type', '=', 'writeoff_button'),
                    ('company_id', '=', wizard.st_line_id.company_id.id),
                    '|',
                    ('match_journal_ids', '=', False),
                    ('match_journal_ids', '=', wizard.st_line_id.journal_id.id),
                ])
                wizard.available_reco_model_ids = [Command.set(available_reco_models.ids)]
            else:
                wizard.available_reco_model_ids = [Command.clear()]

    @api.depends('line_ids.reconcile_model_id')
    def _compute_selected_reco_model_id(self):
        for wizard in self:
            selected_reconcile_models = wizard.line_ids.reconcile_model_id.filtered(lambda x: x.rule_type == 'writeoff_button')
            if len(selected_reconcile_models) == 1:
                wizard.selected_reco_model_id = selected_reconcile_models.id
            else:
                wizard.selected_reco_model_id = None

    @api.depends('st_line_id', 'line_ids.account_id')
    def _compute_state(self):
        for wizard in self:
            if not wizard.st_line_id:
                wizard.state = 'invalid'
            elif wizard.st_line_id.is_reconciled:
                wizard.state = 'reconciled'
            else:
                suspense_account = wizard.st_line_id.journal_id.suspense_account_id
                if suspense_account in wizard.line_ids.account_id:
                    wizard.state = 'invalid'
                else:
                    wizard.state = 'valid'

    @api.depends('st_line_id')
    def _compute_journal_currency_id(self):
        for wizard in self:
            wizard.journal_currency_id = wizard.st_line_id.journal_id.currency_id \
                                         or wizard.st_line_id.journal_id.company_id.currency_id

    def _format_transaction_details(self):
        """ Format the 'transaction_details' field of the statement line to be more readable for the end user.

        Example:
            {
                "debtor": {
                    "name": None,
                    "private_id": None,
                },
                "debtor_account": {
                    "iban": "BE84103080286059",
                    "bank_transaction_code": None,
                    "credit_debit_indicator": "DBIT",
                    "status": "BOOK",
                    "value_date": "2022-12-29",
                    "transaction_date": None,
                    "balance_after_transaction": None,
                },
            }

        Becomes:
            debtor_account:
                iban: BE84103080286059
                credit_debit_indicator: DBIT
                status: BOOK
                value_date: 2022-12-29

        :return: An html representation of the transaction details.
        """
        self.ensure_one()
        details = self.st_line_id.transaction_details
        if not details:
            return

        if isinstance(details, str):
            details = json.loads(details)

        def node_to_html(header, node):
            if not node:
                return ""

            if isinstance(node, dict):
                li_elements = markupsafe.Markup("").join(node_to_html(f"{k}: ", v) for k, v in node.items())
                value = li_elements and markupsafe.Markup('<ol>%s</ol>') % li_elements
            elif isinstance(node, (tuple, list)):
                li_elements = markupsafe.Markup("").join(node_to_html(f"{i}: ", v) for i, v in enumerate(node, start=1))
                value = li_elements and markupsafe.Markup('<ol>%s</ol>') % li_elements
            else:
                value = node

            if not value:
                return ""

            return markupsafe.Markup('<li style="list-style-type: none"><span><span class="fw-bolder">%(header)s</span>%(value)s</span></li>') % {
                'header': header,
                'value': value,
            }

        main_html = node_to_html('', details)
        return markupsafe.Markup("<ol>%s</ol>") % main_html

    @api.depends('st_line_id')
    def _compute_st_line_transaction_details(self):
        for wizard in self:
            wizard.st_line_transaction_details = wizard._format_transaction_details()

    @api.depends('st_line_id')
    def _compute_transaction_currency_id(self):
        for wizard in self:
            wizard.transaction_currency_id = wizard.st_line_id.foreign_currency_id or wizard.journal_currency_id

    @api.depends('st_line_id')
    def _compute_partner_id(self):
        for wizard in self:
            if wizard.st_line_id:
                wizard.partner_id = wizard.st_line_id._retrieve_partner()
            else:
                wizard.partner_id = None

    @api.depends('company_id', 'line_ids.source_aml_id')
    def _compute_selected_aml_ids(self):
        for wizard in self:
            wizard.selected_aml_ids = [Command.set(wizard.line_ids.source_aml_id.ids)]

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('todo_command')
    def _onchange_todo_command(self):
        self.ensure_one()
        todo_command = self.todo_command
        self.todo_command = None
        self.return_todo_command = None

        # Ensure the lines are well loaded.
        # Suppose the initial values of 'line_ids' are 2 lines,
        # "self.line_ids = [Command.create(...)]" will produce a single new line in 'line_ids' but three lines in case
        # the field is accessed before.
        self._ensure_loaded_lines()

        method_name = todo_command['method_name']
        getattr(self, f'_js_action_{method_name}')(*todo_command.get('args', []), **todo_command.get('kwargs', {}))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def new(self, values=None, origin=None, ref=None):
        widget = super().new(values=values, origin=origin, ref=ref)

        # Ensure the lines are well loaded.
        # Suppose the initial values of 'line_ids' are 2 lines,
        # "self.line_ids = [Command.create(...)]" will produce a single new line in 'line_ids' but three lines in case
        # the field is accessed before.
        widget.line_ids

        return widget

    # -------------------------------------------------------------------------
    # INIT
    # -------------------------------------------------------------------------

    @api.model
    def fetch_initial_data(self):
        # Fields.
        fields = self.fields_get()
        field_attributes = self.env['ir.ui.view']._get_view_field_attributes()
        for field_name, field in self._fields.items():
            if field.type == 'one2many':
                fields[field_name]['relatedFields'] = self[field_name]\
                    .fields_get(attributes=field_attributes)
                del fields[field_name]['relatedFields'][field.inverse_name]
                for one2many_fieldname, one2many_field in self[field_name]._fields.items():
                    if one2many_field.type == "many2many":
                        comodel = self.env[one2many_field.comodel_name]
                        fields[field_name]['relatedFields'][one2many_fieldname]['relatedFields'] = comodel \
                            .fields_get(allfields=['id', 'display_name'], attributes=field_attributes)
            elif field.name == 'available_reco_model_ids':
                fields[field_name]['relatedFields'] = self[field_name]\
                    .fields_get(allfields=['id', 'display_name'], attributes=field_attributes)

        fields['todo_command']['onChange'] = True

        # Initial values.
        initial_values = {}
        for field_name, field in self._fields.items():
            if field.type == 'one2many':
                initial_values[field_name] = []
            else:
                initial_values[field_name] = field.convert_to_onchange(self[field_name], self, {})

        return {
            'initial_values': initial_values,
            'fields': fields,
        }

    # -------------------------------------------------------------------------
    # LINES METHODS
    # -------------------------------------------------------------------------

    def _ensure_loaded_lines(self):
        # Ensure the lines are well loaded.
        # Suppose the initial values of 'line_ids' are 2 lines,
        # "self.line_ids = [Command.create(...)]" will produce a single new line in 'line_ids' but three lines in case
        # the field is accessed before.
        self.line_ids

    def _lines_turn_auto_balance_into_manual_line(self, line):
        # When editing an auto_balance line, it becomes a custom manual line.
        if line.flag == 'auto_balance':
            line.flag = 'manual'

    def _lines_get_line_in_edit_form(self):
        self.ensure_one()

        if not self.form_index:
            return

        return self.line_ids.filtered(lambda x: x.index == self.form_index)

    def _lines_prepare_aml_line(self, aml, **kwargs):
        self.ensure_one()
        return {
            'flag': 'aml',
            'source_aml_id': aml,
            **kwargs,
        }

    def _lines_prepare_liquidity_line(self):
        """ Create a line corresponding to the journal item having the liquidity account on the statement line."""
        self.ensure_one()
        st_line = self.st_line_id

        # In case of a different currencies on the journal and on the transaction, we need to retrieve the transaction
        # amount on the suspense line because a journal item can only have one foreign currency. Indeed, in such
        # configuration, the foreign currency amount expressed in journal's currency is set on the liquidity line but
        # the transaction amount is on the suspense account line.
        liquidity_line, _suspense_lines, _other_lines = st_line._seek_for_lines()

        return self._lines_prepare_aml_line(liquidity_line, flag='liquidity')

    def _lines_prepare_auto_balance_line(self):
        """ Create the auto_balance line if necessary in order to have fully balanced lines."""
        self.ensure_one()
        st_line = self.st_line_id

        # Compute the current open balance.
        transaction_amount, transaction_currency, journal_amount, _journal_currency, company_amount, _company_currency \
            = self.st_line_id._get_accounting_amounts_and_currencies()
        open_amount_currency = -transaction_amount
        open_balance = -company_amount
        for line in self.line_ids:
            if line.flag in ('liquidity', 'auto_balance'):
                continue

            open_balance -= line.balance
            journal_transaction_rate = abs(transaction_amount / journal_amount) if journal_amount else 0.0
            company_transaction_rate = abs(transaction_amount / company_amount) if company_amount else 0.0
            if line.currency_id == self.transaction_currency_id:
                open_amount_currency -= line.amount_currency
            elif line.currency_id == self.journal_currency_id:
                open_amount_currency -= transaction_currency.round(line.amount_currency * journal_transaction_rate)
            else:
                open_amount_currency -= transaction_currency.round(line.balance * company_transaction_rate)

        # Create a new auto-balance line.
        account = None
        partner = self.partner_id
        if partner:
            name = _("Open balance: %s", st_line.payment_ref)
            partner_is_customer = partner.customer_rank and not partner.supplier_rank
            partner_is_supplier = partner.supplier_rank and not partner.customer_rank
            if partner_is_customer:
                account = partner.with_company(st_line.company_id).property_account_receivable_id
            elif partner_is_supplier:
                account = partner.with_company(st_line.company_id).property_account_payable_id
            elif st_line.amount > 0:
                account = partner.with_company(st_line.company_id).property_account_receivable_id
            else:
                account = partner.with_company(st_line.company_id).property_account_payable_id

        if not account:
            name = st_line.payment_ref
            account = st_line.journal_id.suspense_account_id

        return {
            'flag': 'auto_balance',

            'account_id': account.id,
            'name': name,
            'amount_currency': open_amount_currency,
            'balance': open_balance,
        }

    def _lines_add_auto_balance_line(self):
        ''' Add the line auto balancing the debit/credit. '''

        # Drop the existing line then re-create it to ensure this line is always the last one.
        line_ids_commands = []
        for auto_balance_line in self.line_ids.filtered(lambda x: x.flag == 'auto_balance'):
            line_ids_commands.append(Command.unlink(auto_balance_line.id))

        # Re-create a new auto-balance line if needed.
        auto_balance_line_vals = self._lines_prepare_auto_balance_line()
        if not self.company_currency_id.is_zero(auto_balance_line_vals['balance']):
            line_ids_commands.append(Command.create(auto_balance_line_vals))
        self.line_ids = line_ids_commands

    def _lines_prepare_new_aml_line(self, aml, **kwargs):
        return self._lines_prepare_aml_line(
            aml,
            flag='new_aml',
            currency_id=aml.currency_id,
            amount_currency=-aml.amount_residual_currency,
            balance=-aml.amount_residual,
            source_amount_currency=-aml.amount_residual_currency,
            source_balance=-aml.amount_residual,
            **kwargs,
        )

    def _lines_check_partial_amount(self, line):
        if line.flag != 'new_aml':
            return None

        exchange_diff_line = self.line_ids\
            .filtered(lambda x: x.flag == 'exchange_diff' and x.source_aml_id == line.source_aml_id)
        auto_balance_line_vals = self._lines_prepare_auto_balance_line()

        auto_balance = auto_balance_line_vals['balance']
        current_balance = line.balance + exchange_diff_line.balance
        has_enough_comp_debit = self.company_currency_id.compare_amounts(auto_balance, 0) < 0 \
                                and self.company_currency_id.compare_amounts(current_balance, 0) > 0 \
                                and self.company_currency_id.compare_amounts(current_balance, -auto_balance) > 0
        has_enough_comp_credit = self.company_currency_id.compare_amounts(auto_balance, 0) > 0 \
                                and self.company_currency_id.compare_amounts(current_balance, 0) < 0 \
                                and self.company_currency_id.compare_amounts(-current_balance, auto_balance) > 0

        auto_amount_currency = auto_balance_line_vals['amount_currency']
        current_amount_currency = line.amount_currency
        has_enough_curr_debit = line.currency_id.compare_amounts(auto_amount_currency, 0) < 0 \
                                and line.currency_id.compare_amounts(current_amount_currency, 0) > 0 \
                                and line.currency_id.compare_amounts(current_amount_currency, -auto_amount_currency) > 0
        has_enough_curr_credit = line.currency_id.compare_amounts(auto_amount_currency, 0) > 0 \
                                and line.currency_id.compare_amounts(current_amount_currency, 0) < 0 \
                                and line.currency_id.compare_amounts(-current_amount_currency, auto_amount_currency) > 0

        if line.currency_id == self.transaction_currency_id:
            if has_enough_curr_debit or has_enough_curr_credit:
                amount_currency_after_partial = current_amount_currency + auto_amount_currency

                # Get the bank transaction rate.
                transaction_amount, _transaction_currency, _journal_amount, _journal_currency, company_amount, _company_currency \
                    = self.st_line_id._get_accounting_amounts_and_currencies()
                rate = abs(company_amount / transaction_amount) if transaction_amount else 0.0

                # Compute the amounts to make a partial.
                balance_after_partial = line.company_currency_id.round(amount_currency_after_partial * rate)
                new_line_balance = line.company_currency_id.round(balance_after_partial * abs(line.balance) / abs(current_balance))
                exchange_diff_line_balance = balance_after_partial - new_line_balance
                return {
                    'exchange_diff_line': exchange_diff_line,
                    'amount_currency': amount_currency_after_partial,
                    'balance': new_line_balance,
                    'exchange_balance': exchange_diff_line_balance,
                }
        elif has_enough_comp_debit or has_enough_comp_credit:
            # Compute the new value for balance.
            balance_after_partial = current_balance + auto_balance

            # Get the rate of the original journal item.
            rate = abs(line.source_amount_currency) / abs(line.source_balance)

            # Compute the amounts to make a partial.
            new_line_balance = line.company_currency_id.round(balance_after_partial * abs(line.balance) / abs(current_balance))
            exchange_diff_line_balance = balance_after_partial - new_line_balance
            amount_currency_after_partial = line.currency_id.round(new_line_balance * rate)
            return {
                'exchange_diff_line': exchange_diff_line,
                'amount_currency': amount_currency_after_partial,
                'balance': new_line_balance,
                'exchange_balance': exchange_diff_line_balance,
            }
        return None

    def _lines_check_apply_early_payment_discount(self):
        """ Try to apply the early payment discount on the currently mounted journal items.
        :return: True if applied, False otherwise.
        """
        all_aml_lines = self.line_ids.filtered(lambda x: x.flag == 'new_aml')

        # Get the balance without the 'new_aml' lines.
        auto_balance_line_vals = self._lines_prepare_auto_balance_line()
        open_balance_wo_amls = auto_balance_line_vals['balance'] + sum(all_aml_lines.mapped('balance'))
        open_amount_currency_wo_amls = auto_balance_line_vals['amount_currency'] + sum(all_aml_lines.mapped('amount_currency'))

        # Get the balance after adding the 'new_aml' lines but without considering the partial amounts.
        open_balance = open_balance_wo_amls - sum(all_aml_lines.mapped('source_balance'))
        open_amount_currency = open_amount_currency_wo_amls - sum(all_aml_lines.mapped('source_amount_currency'))

        is_same_currency = all_aml_lines.currency_id == self.transaction_currency_id
        at_least_one_aml_for_early_payment = False

        early_pay_aml_values_list = []
        total_early_payment_discount = 0.0

        for aml_line in all_aml_lines:
            aml = aml_line.source_aml_id

            if aml.move_id._is_eligible_for_early_payment_discount(self.transaction_currency_id, self.st_line_id.date):
                at_least_one_aml_for_early_payment = True
                total_early_payment_discount += aml.amount_currency - aml.discount_amount_currency

                early_pay_aml_values_list.append({
                    'aml': aml,
                    'amount_currency': aml_line.amount_currency,
                    'balance': aml_line.balance,
                })

        line_ids_create_command_list = []
        is_early_payment_applied = False

        # Cleanup the existing early payment discount lines.
        for line in self.line_ids.filtered(lambda x: x.flag == 'early_payment'):
            line_ids_create_command_list.append(Command.unlink(line.id))

        if is_same_currency \
            and at_least_one_aml_for_early_payment \
            and self.transaction_currency_id.compare_amounts(open_amount_currency, total_early_payment_discount) == 0:
            # == Compute the early payment discount lines ==
            # Remove the partials on existing lines.
            for aml_line in all_aml_lines:
                aml_line.amount_currency = aml_line.source_amount_currency
                aml_line.balance = aml_line.source_balance

            # Add the early payment lines.
            early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(
                early_pay_aml_values_list,
                open_balance,
            )

            for vals_list in early_payment_values.values():
                for vals in vals_list:
                    line_ids_create_command_list.append(Command.create({
                        'flag': 'early_payment',
                        'account_id': vals['account_id'],
                        'date': self.st_line_id.date,
                        'name': vals['name'],
                        'partner_id': vals['partner_id'],
                        'currency_id': vals['currency_id'],
                        'amount_currency': vals['amount_currency'],
                        'balance': vals['balance'],
                        'analytic_distribution': vals.get('analytic_distribution'),
                        'tax_ids': vals.get('tax_ids', []),
                        'tax_tag_ids': vals.get('tax_tag_ids', []),
                        'tax_repartition_line_id': vals.get('tax_repartition_line_id'),
                        'group_tax_id': vals.get('group_tax_id'),
                    }))
                    is_early_payment_applied = True

        if line_ids_create_command_list:
            self.line_ids = line_ids_create_command_list

        return is_early_payment_applied

    def _lines_check_apply_partial_matching(self):
        """ Try to apply a partial matching on the currently mounted journal items.
        :return: True if applied, False otherwise.
        """
        all_aml_lines = self.line_ids.filtered(lambda x: x.flag == 'new_aml')
        if all_aml_lines:
            last_line = all_aml_lines[-1]

            # Cleanup the existing partials if not on the last line.
            line_ids_commands = []
            for aml_line in all_aml_lines:
                is_partial = aml_line.display_stroked_amount_currency or aml_line.display_stroked_balance
                if is_partial and not aml_line.manually_modified:
                    line_ids_commands.append(Command.update(aml_line.id, {
                        'amount_currency': aml_line.source_amount_currency,
                        'balance': aml_line.source_balance,
                    }))
            if line_ids_commands:
                self.line_ids = line_ids_commands
                self._lines_recompute_exchange_diff()

            # Check for a partial reconciliation.
            partial_amounts = self._lines_check_partial_amount(last_line)

            if partial_amounts:
                # Make a partial: an auto-balance line is no longer necessary.
                last_line.amount_currency = partial_amounts['amount_currency']
                last_line.balance = partial_amounts['balance']
                exchange_line = partial_amounts['exchange_diff_line']
                if exchange_line:
                    exchange_line.balance = partial_amounts['exchange_balance']
                    if exchange_line.currency_id == self.company_currency_id:
                        exchange_line.amount_currency = exchange_line.balance
                return True

        return False

    def _lines_load_new_amls(self, amls, reco_model=None):
        """ Create counterpart lines for the journal items passed as parameter."""
        # Create a new line for each aml.
        line_ids_commands = []
        kwargs = {'reconcile_model_id': reco_model.id} if reco_model else {}
        for aml in amls:
            aml_line_vals = self._lines_prepare_new_aml_line(aml, **kwargs)
            line_ids_commands.append(Command.create(aml_line_vals))

        if not line_ids_commands:
            return

        self.line_ids = line_ids_commands

    def _convert_to_tax_base_line_dict(self, line):
        """ Convert the current dictionary in order to use the generic taxes computation method defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()
        tax_type = line.tax_ids[0].type_tax_use if line.tax_ids else None
        is_refund = (tax_type == 'sale' and line.balance > 0.0) or (tax_type == 'purchase' and line.balance < 0.0)

        if line.force_price_included_taxes:
            handle_price_include = True
            extra_context = {'force_price_include': True}
            base_amount = line.tax_base_amount_currency
        else:
            handle_price_include = False
            extra_context = None
            base_amount = line.amount_currency

        return self.env['account.tax']._convert_to_tax_base_line_dict(
            line,
            partner=line.partner_id,
            currency=line.currency_id,
            taxes=line.tax_ids,
            price_unit=base_amount,
            quantity=1.0,
            account=line.account_id,
            analytic_distribution=line.analytic_distribution,
            price_subtotal=base_amount,
            is_refund=is_refund,
            handle_price_include=handle_price_include,
            extra_context=extra_context,
        )

    def _convert_to_tax_line_dict(self, line):
        """ Convert the current dictionary in order to use the generic taxes computation method defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()

        return self.env['account.tax']._convert_to_tax_line_dict(
            line,
            partner=line.partner_id,
            currency=line.currency_id,
            taxes=line.tax_ids,
            tax_tags=line.tax_tag_ids,
            tax_repartition_line=line.tax_repartition_line_id,
            group_tax=line.group_tax_id,
            account=line.account_id,
            analytic_distribution=line.analytic_distribution,
            tax_amount=line.amount_currency,
        )

    def _lines_prepare_tax_line(self, tax_line_vals):
        self.ensure_one()

        tax_rep = self.env['account.tax.repartition.line'].browse(tax_line_vals['tax_repartition_line_id'])
        name = tax_rep.tax_id.name
        if self.st_line_id.payment_ref:
            name = f'{name} - {self.st_line_id.payment_ref}'
        if tax_line_vals['tax_id'] == tax_rep.tax_id.id:
            group_tax = self.env['account.tax']
        else:
            group_tax = self.env['account.tax'].browse(tax_line_vals['tax_id'])
        currency = self.env['res.currency'].browse(tax_line_vals['currency_id'])
        amount_currency = tax_line_vals['tax_amount']
        balance = self.st_line_id._prepare_counterpart_amounts_using_st_line_rate(currency, None, amount_currency)['balance']

        return {
            'flag': 'tax_line',

            'account_id': tax_line_vals['account_id'],
            'date': self.st_line_id.date,
            'name': name,
            'partner_id': tax_line_vals['partner_id'],
            'currency_id': currency.id,
            'amount_currency': amount_currency,
            'balance': balance,

            'analytic_distribution': tax_line_vals['analytic_distribution'],
            'tax_repartition_line_id': tax_rep.id,
            'tax_ids': tax_line_vals['tax_ids'],
            'tax_tag_ids': tax_line_vals['tax_tag_ids'],
            'group_tax_id': group_tax.id,
        }

    def _lines_recompute_taxes(self):
        self.ensure_one()
        base_lines = self.line_ids.filtered(lambda x: x.flag == 'manual' and not x.tax_repartition_line_id and x.tax_ids)
        tax_lines = self.line_ids.filtered(lambda x: x.flag == 'tax_line')

        tax_results = self.env['account.tax']._compute_taxes(
            [self._convert_to_tax_base_line_dict(x) for x in base_lines],
            tax_lines=[self._convert_to_tax_line_dict(x) for x in tax_lines],
            include_caba_tags=True,
        )

        line_ids_commands = []

        # Update the base lines.
        for base_line_vals, to_update in tax_results['base_lines_to_update']:
            line = base_line_vals['record']
            amount_currency = to_update['price_subtotal']
            if line.flag == 'new_aml':
                rate = abs(line.source_amount_currency) / abs(line.source_balance)
                balance = line.company_currency_id.round(amount_currency / rate)
            else:
                balance = self.st_line_id\
                    ._prepare_counterpart_amounts_using_st_line_rate(line.currency_id, line.source_balance, amount_currency)['balance']

            line_ids_commands.append(Command.update(line.id, {
                'balance': balance,
                'amount_currency': amount_currency,
                'tax_tag_ids': to_update['tax_tag_ids'],
            }))

        # Tax lines that are no longer needed.
        for tax_line_vals in tax_results['tax_lines_to_delete']:
            line_ids_commands.append(Command.unlink(tax_line_vals['record'].id))

        # Newly created tax lines.
        for tax_line_vals in tax_results['tax_lines_to_add']:
            line_ids_commands.append(Command.create(self._lines_prepare_tax_line(tax_line_vals)))

        # Update of existing tax lines.
        for tax_line_vals, to_update in tax_results['tax_lines_to_update']:
            new_line_vals = self._lines_prepare_tax_line(to_update)
            line_ids_commands.append(Command.update(tax_line_vals['record'].id, {
                'amount_currency': new_line_vals['amount_currency'],
                'balance': new_line_vals['balance'],
            }))

        self.line_ids = line_ids_commands

    def _lines_recompute_exchange_diff(self):
        self.ensure_one()
        line_ids_commands = []

        # Clean the existing lines.
        for exchange_diff in self.line_ids.filtered(lambda x: x.flag == 'exchange_diff'):
            line_ids_commands.append(Command.unlink(exchange_diff.id))

        new_amls = self.line_ids.filtered(lambda x: x.flag == 'new_aml')
        for new_aml in new_amls:

            # Compute the balance of the line using the rate/currency coming from the bank transaction.
            amounts_in_st_curr = self.st_line_id._prepare_counterpart_amounts_using_st_line_rate(
                new_aml.currency_id,
                new_aml.balance,
                new_aml.amount_currency,
            )
            balance = amounts_in_st_curr['balance']
            if new_aml.currency_id == self.company_currency_id and self.transaction_currency_id != self.company_currency_id:
                # The reconciliation will be expressed using the rate of the statement line.
                balance = new_aml.balance
            elif new_aml.currency_id != self.company_currency_id and self.transaction_currency_id == self.company_currency_id:
                # The reconciliation will be expressed using the foreign currency of the aml to cover the Mexican
                # case.
                balance = new_aml.currency_id\
                    ._convert(new_aml.amount_currency, self.transaction_currency_id, self.company_id, self.st_line_id.date)

            # Compute the exchange difference balance.
            exchange_diff_balance = balance - new_aml.balance
            if self.company_currency_id.is_zero(exchange_diff_balance):
                continue

            expense_exchange_account = self.company_id.expense_currency_exchange_account_id
            income_exchange_account = self.company_id.income_currency_exchange_account_id

            if exchange_diff_balance > 0.0:
                account = expense_exchange_account
            else:
                account = income_exchange_account

            line_ids_commands.append(Command.create({
                'flag': 'exchange_diff',
                'source_aml_id': new_aml.source_aml_id.id,
                'account_id': account.id,
                'date': new_aml.date,
                'name': _("Exchange Difference: %s", new_aml.name),
                'partner_id': new_aml.partner_id.id,
                'currency_id': new_aml.currency_id.id,
                'amount_currency': exchange_diff_balance if new_aml.currency_id == self.company_currency_id else 0.0,
                'balance': exchange_diff_balance,
            }))

        if line_ids_commands:
            self.line_ids = line_ids_commands

            # Reorder to put each exchange line right after the corresponding new_aml.
            new_lines_ids = []
            source2exchange = self.line_ids.filtered(lambda x: x.flag == 'exchange_diff').grouped('source_aml_id')
            for line in self.line_ids:
                if line.flag == 'exchange_diff':
                    continue

                new_lines_ids.append(line.id)
                if line.flag == 'new_aml':
                    exchange_diff = source2exchange.get(line.source_aml_id)
                    if exchange_diff:
                        new_lines_ids.append(source2exchange.get(line.source_aml_id).id)
            self.line_ids = self.env['bank.rec.widget.line'].browse(new_lines_ids)

    def _lines_prepare_reco_model_write_off_vals(self, reco_model, write_off_vals):
        self.ensure_one()

        balance = self.st_line_id\
            ._prepare_counterpart_amounts_using_st_line_rate(self.transaction_currency_id, None, write_off_vals['amount_currency'])['balance']

        return {
            'flag': 'manual',

            'account_id': write_off_vals['account_id'],
            'date': self.st_line_id.date,
            'name': write_off_vals['name'],
            'partner_id': write_off_vals['partner_id'],
            'currency_id': write_off_vals['currency_id'],
            'amount_currency': write_off_vals['amount_currency'],
            'balance': balance,
            'tax_base_amount_currency': write_off_vals['amount_currency'],
            'force_price_included_taxes': True,

            'reconcile_model_id': reco_model.id,
            'analytic_distribution': write_off_vals['analytic_distribution'],
            'tax_ids': write_off_vals['tax_ids'],
        }

    # -------------------------------------------------------------------------
    # LINES UPDATE METHODS
    # -------------------------------------------------------------------------

    def _line_value_changed_account_id(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

        # Recompute taxes.
        if line.flag not in ('tax_line', 'early_payment') and line.tax_ids:
            self._lines_recompute_taxes()
            self._lines_add_auto_balance_line()

    def _line_value_changed_date(self, line):
        self.ensure_one()
        if line.flag == 'liquidity' and line.date:
            self.st_line_id.date = line.date
            self._action_reload_liquidity_line()
            self.return_todo_command = {'reset_global_info': True, 'reset_record': True}

    def _line_value_changed_narration(self, line):
        self.ensure_one()
        if line.flag == 'liquidity':
            self.st_line_id.move_id.narration = line.narration
            self._action_reload_liquidity_line()
            self.return_todo_command = {'reset_record': True}

    def _line_value_changed_name(self, line):
        self.ensure_one()
        if line.flag == 'liquidity':
            self.st_line_id.payment_ref = line.name
            self._action_reload_liquidity_line()
            self.return_todo_command = {'reset_global_info': True, 'reset_record': True}
            return

        self._lines_turn_auto_balance_into_manual_line(line)

    def _line_value_changed_amount_currency(self, line):
        self.ensure_one()
        if line.flag == 'liquidity':
            self.st_line_id.amount = line.amount_currency
            self.return_todo_command = {'reset_global_info': True}
            return

        self._lines_turn_auto_balance_into_manual_line(line)

        sign = -1 if line.amount_currency < 0.0 else 1
        if line.flag == 'new_aml':
            # The balance must keep the same sign as the original aml and must not exceed its original value.
            line.amount_currency = sign * max(0.0, min(abs(line.amount_currency), abs(line.source_amount_currency)))
            line.manually_modified = True

            # If the user remove completely the value, reset to the original balance.
            if not line.amount_currency:
                line.amount_currency = line.source_amount_currency

        elif not line.amount_currency:
            line.amount_currency = 0.0

        if line.currency_id == line.company_currency_id:
            # Single currency: amount_currency must be equal to balance.
            line.balance = line.amount_currency
        elif line.flag == 'new_aml':
            if line.currency_id.compare_amounts(abs(line.amount_currency), abs(line.source_amount_currency)) == 0.0:
                # The value has been reset to its original value. Reset the balance as well to avoid rounding issues.
                line.balance = line.source_balance
            else:
                # Apply the rate.
                if line.source_balance:
                    rate = abs(line.source_amount_currency / line.source_balance)
                    line.balance = line.company_currency_id.round(line.amount_currency / rate)
                else:
                    line.balance = 0.0
        elif line.flag in ('manual', 'early_payment', 'tax_line'):
            if line.currency_id in (self.transaction_currency_id, self.journal_currency_id):
                line.balance = self.st_line_id\
                    ._prepare_counterpart_amounts_using_st_line_rate(line.currency_id, None, line.amount_currency)['balance']
            else:
                line.balance = line.currency_id\
                    ._convert(line.amount_currency, self.company_currency_id, self.company_id, self.st_line_id.date)

        if line.flag not in ('tax_line', 'early_payment'):
            if line.tax_ids:
                # Manual edition of amounts. Disable the price_included mode.
                line.force_price_included_taxes = False
                self._lines_recompute_taxes()
            self._lines_recompute_exchange_diff()

        self._lines_add_auto_balance_line()

    def _line_value_changed_balance(self, line):
        self.ensure_one()
        if line.flag == 'liquidity':
            self.st_line_id.amount = line.balance
            self._action_reload_liquidity_line()
            self.return_todo_command = {'reset_global_info': True, 'reset_record': True}
            return

        self._lines_turn_auto_balance_into_manual_line(line)

        sign = -1 if line.balance < 0.0 else 1
        if line.flag == 'new_aml':
            # The balance must keep the same sign as the original aml and must not exceed its original value.
            line.balance = sign * max(0.0, min(abs(line.balance), abs(line.source_balance)))
            line.manually_modified = True

            # If the user remove completely the value, reset to the original balance.
            if not line.balance:
                line.balance = line.source_balance

        elif not line.balance:
            line.balance = 0.0

        # Single currency: amount_currency must be equal to balance.
        if line.currency_id == line.company_currency_id:
            line.amount_currency = line.balance
            self._line_value_changed_amount_currency(line)
        else:
            self._lines_recompute_exchange_diff()
            self._lines_add_auto_balance_line()

    def _line_value_changed_currency_id(self, line):
        self.ensure_one()
        self._line_value_changed_amount_currency(line)

    def _line_value_changed_tax_ids(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

        if line.tax_ids:
            # Adding taxes but no tax before.
            if not line.tax_base_amount_currency:
                line.tax_base_amount_currency = line.amount_currency
                line.force_price_included_taxes = True
        else:
            original_base_amount_currency = line.tax_base_amount_currency
            line.tax_base_amount_currency = False
            if line.force_price_included_taxes:
                # Removing taxes letting the field empty.
                # If the user didn't touch the amount_currency/balance, restore the original amount.
                line.amount_currency = original_base_amount_currency
                line.tax_base_amount_currency = False
                self._line_value_changed_amount_currency(line)

        self._lines_recompute_taxes()
        self._lines_add_auto_balance_line()

    def _line_value_changed_partner_id(self, line):
        self.ensure_one()
        if line.flag == 'liquidity':
            self.st_line_id.partner_id = line.partner_id
            self._action_reload_liquidity_line()
            self.return_todo_command = {'reset_global_info': True, 'reset_record': True}
            return

        self._lines_turn_auto_balance_into_manual_line(line)

        new_account = None
        if line.partner_id:
            partner_is_customer = line.partner_id.customer_rank and not line.partner_id.supplier_rank
            partner_is_supplier = line.partner_id.supplier_rank and not line.partner_id.customer_rank
            is_partner_receivable_amount_zero = line.partner_currency_id.is_zero(line.partner_receivable_amount)
            is_partner_payable_amount_zero = line.partner_currency_id.is_zero(line.partner_payable_amount)
            if partner_is_customer or not is_partner_receivable_amount_zero and is_partner_payable_amount_zero:
                new_account = line.partner_receivable_account_id
            elif partner_is_supplier or is_partner_receivable_amount_zero and not is_partner_payable_amount_zero:
                new_account = line.partner_payable_account_id
            elif self.st_line_id.amount < 0.0:
                new_account = line.partner_payable_account_id or line.partner_receivable_account_id
            else:
                new_account = line.partner_receivable_account_id or line.partner_payable_account_id

        if new_account:
            # Set the new receivable/payable account if any.
            line.account_id = new_account
            self._line_value_changed_account_id(line)
        elif line.flag not in ('tax_line', 'early_payment') and line.tax_ids:
            # Recompute taxes.
            self._lines_recompute_taxes()
            self._lines_add_auto_balance_line()

    def _line_value_changed_analytic_distribution(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

        # Recompute taxes.
        if line.flag not in ('tax_line', 'early_payment') and any(x.analytic for x in line.tax_ids):
            self._lines_recompute_taxes()
            self._lines_add_auto_balance_line()

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def _action_trigger_matching_rules(self):
        self.ensure_one()

        if self.st_line_id.is_reconciled:
            return

        reconcile_models = self.env['account.reconcile.model'].search([
            ('rule_type', '!=', 'writeoff_button'),
            ('company_id', '=', self.company_id.id),
            '|',
            ('match_journal_ids', '=', False),
            ('match_journal_ids', '=', self.st_line_id.journal_id.id),
        ])
        matching = reconcile_models._apply_rules(self.st_line_id, self.partner_id)

        if matching.get('amls'):
            reco_model = matching['model']
            # In case there is a write-off, keep the whole amount and let the write-off doing the auto-balancing.
            allow_partial = matching.get('status') != 'write_off'
            self._action_add_new_amls(matching['amls'], reco_model=reco_model, allow_partial=allow_partial)
        if matching.get('status') == 'write_off':
            reco_model = matching['model']
            self._action_select_reconcile_model(reco_model)
        if matching.get('auto_reconcile'):
            self.matching_rules_allow_auto_reconcile = True
        return matching

    def _prepare_embedded_views_data(self):
        self.ensure_one()
        st_line = self.st_line_id

        context = {
            'search_view_ref': 'account_accountant.view_account_move_line_search_bank_rec_widget',
            'tree_view_ref': 'account_accountant.view_account_move_line_list_bank_rec_widget',
        }

        if self.partner_id:
            context['search_default_partner_id'] = self.partner_id.id

        dynamic_filters = []

        # == Dynamic Customer/Vendor filter ==
        journal = st_line.journal_id

        account_ids = set()

        inbound_accounts = journal._get_journal_inbound_outstanding_payment_accounts() - journal.default_account_id
        outbound_accounts = journal._get_journal_outbound_outstanding_payment_accounts() - journal.default_account_id

        # Matching on debit account.
        for account in inbound_accounts:
            account_ids.add(account.id)

        # Matching on credit account.
        for account in outbound_accounts:
            account_ids.add(account.id)

        rec_pay_matching_filter = {
            'name': 'receivable_payable_matching',
            'description': _("Customer/Vendor"),
            'domain': [
                '|',
                # Matching invoices.
                '&',
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('payment_id', '=', False),
                # Matching Payments.
                '&',
                ('account_id', 'in', tuple(account_ids)),
                ('payment_id', '!=', False),
            ],
            'no_separator': True,
            'is_default': False,
        }

        misc_matching_filter = {
            'name': 'misc_matching',
            'description': _("Misc"),
            'domain': ['!'] + rec_pay_matching_filter['domain'],
            'is_default': False,
        }

        dynamic_filters.append(rec_pay_matching_filter)
        dynamic_filters.append(misc_matching_filter)

        # Stringify the domain.
        for dynamic_filter in dynamic_filters:
            dynamic_filter['domain'] = str(dynamic_filter['domain'])

        return {
            'amls': {
                'domain': st_line._get_default_amls_matching_domain(),
                'dynamic_filters': dynamic_filters,
                'context': context,
            },
        }

    def _action_mount_st_line(self, st_line):
        self.ensure_one()
        self.st_line_id = st_line
        self.form_index = None
        self._action_trigger_matching_rules()

    def _js_action_mount_st_line(self, st_line_id):
        self.ensure_one()
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)
        self._action_mount_st_line(st_line)
        self.return_todo_command = self._prepare_embedded_views_data()

    def _js_action_restore_st_line_data(self, initial_data):
        self.ensure_one()
        initial_values = initial_data['initial_values']

        self.st_line_id = self.env['account.bank.statement.line'].browse(initial_values['st_line_id'])

        # Skip restore and trigger matching rules if the liquidity line was modified
        liquidity_line = self.line_ids.filtered(lambda l: l.flag == 'liquidity')
        initial_liquidity_line_values = next((cmd[2] for cmd in initial_values['line_ids'] if cmd[2]['flag'] == 'liquidity'), {})
        initial_liquidity_line = self.env['bank.rec.widget.line'].new(initial_liquidity_line_values)
        for field in initial_liquidity_line_values.keys() - ['index', 'suggestion_html']:
            if initial_liquidity_line[field] != liquidity_line[field]:
                self._js_action_mount_st_line(self.st_line_id.id)
                return

        # If the user goes to reco model and create a new one, we want to make it appearing when coming back.
        # That's why we pop 'available_reco_model_ids' as well.
        for field_name in ('id', 'st_line_id', 'todo_command', 'return_todo_command', 'available_reco_model_ids'):
            initial_values.pop(field_name, None)

        line_ids_commands = [Command.clear()]
        for orm_command in initial_values['line_ids']:
            if orm_command[0] == Command.CREATE:
                line_ids_commands.append(Command.create(orm_command[2]))
            else:
                line_ids_commands.append(orm_command)
        initial_values['line_ids'] = line_ids_commands

        self.update(initial_values)

        self.return_todo_command = self._prepare_embedded_views_data()

    def _action_reload_liquidity_line(self):
        self.ensure_one()
        self = self.with_context(default_st_line_id=self.st_line_id.id)

        self.invalidate_model()

        # Ensure the lines are well loaded.
        # Suppose the initial values of 'line_ids' are 2 lines,
        # "self.line_ids = [Command.create(...)]" will produce a single new line in 'line_ids' but three lines in case
        # the field is accessed before.
        self.line_ids

        self._action_trigger_matching_rules()

        # Focus back the liquidity line.
        self._js_action_mount_line_in_edit(self.line_ids.filtered(lambda x: x.flag == 'liquidity').index)

    def _action_validate(self):
        self.ensure_one()
        partners = (self.line_ids.filtered(lambda x: x.flag != 'liquidity')).partner_id
        partner_to_set = partners if len(partners) == 1 else self.env['res.partner']

        # Prepare the lines to be created.
        to_reconcile = []
        line_ids_create_command_list = []
        aml_to_exchange_diff_vals = {}

        source2exchange = self.line_ids.filtered(lambda l: l.flag == 'exchange_diff').grouped('source_aml_id')
        for i, line in enumerate(self.line_ids):
            if line.flag == 'exchange_diff':
                continue

            amount_currency = line.amount_currency
            balance = line.balance
            if line.flag == 'new_aml':
                to_reconcile.append((i, line.source_aml_id))
                exchange_diff = source2exchange.get(line.source_aml_id)
                if exchange_diff:
                    aml_to_exchange_diff_vals[i] = {
                        'amount_residual': exchange_diff.balance,
                        'amount_residual_currency': exchange_diff.amount_currency,
                        'analytic_distribution': exchange_diff.analytic_distribution,
                    }
                    # Squash amounts of exchange diff into corresponding new_aml
                    amount_currency += exchange_diff.amount_currency
                    balance += exchange_diff.balance
            line_ids_create_command_list.append(Command.create(line._get_aml_values(
                sequence=i,
                partner_id=partner_to_set.id if line.flag in ('liquidity', 'auto_balance') else line.partner_id.id,
                amount_currency=amount_currency,
                balance=balance,
            )))

        st_line = self.st_line_id
        move = st_line.move_id

        # Update the move.
        move_ctx = move.with_context(
            force_delete=True,
        )
        move_ctx.write({'partner_id': partner_to_set.id, 'line_ids': [Command.clear()] + line_ids_create_command_list})
        if move_ctx.state == 'draft':
            move_ctx.action_post()

        AccountMoveLine = self.env['account.move.line']
        sequence2lines = move_ctx.line_ids.grouped('sequence')
        lines = [
            (sequence2lines[index], counterpart_aml)
            for index, counterpart_aml in to_reconcile
        ]
        all_line_ids = tuple({_id for line, counterpart in lines for _id in (line + counterpart).ids})
        # Handle exchange diffs
        exchange_diff_moves = None
        lines_with_exch_diff = AccountMoveLine
        if aml_to_exchange_diff_vals:
            exchange_diff_vals_list = []
            for line, counterpart in lines:
                line = line.with_prefetch(all_line_ids)
                counterpart = counterpart.with_prefetch(all_line_ids)
                exchange_diff_amounts = aml_to_exchange_diff_vals.get(line.sequence, {})
                exchange_analytic_distribution = exchange_diff_amounts.pop('analytic_distribution', False)
                if exchange_diff_amounts:
                    related_exchange_diff_amls = line if exchange_diff_amounts['amount_residual'] * line.amount_residual > 0 else counterpart
                    exchange_diff_vals_list.append(related_exchange_diff_amls._prepare_exchange_difference_move_vals(
                        [exchange_diff_amounts],
                        exchange_date=max(line.date, counterpart.date),
                        exchange_analytic_distribution=exchange_analytic_distribution,
                    ))
                    lines_with_exch_diff += line
            exchange_diff_moves = AccountMoveLine._create_exchange_difference_moves(exchange_diff_vals_list)

        # Perform the reconciliation.
        self.env['account.move.line'].with_context(no_exchange_difference=True)._reconcile_plan(
            [(line + counterpart).with_prefetch(all_line_ids) for line, counterpart in lines])

        # Assign exchange move to partials.
        for index, line in enumerate(lines_with_exch_diff):
            exchange_move = exchange_diff_moves[index]
            for debit_credit in ('debit', 'credit'):
                partials = line[f'matched_{debit_credit}_ids'] \
                    .filtered(lambda partial: partial[f'{debit_credit}_move_id'].move_id != exchange_move)
                partials.exchange_move_id = exchange_move

        # Fill missing partner.
        st_line_ctx = st_line.with_context(skip_account_move_synchronization=True)
        st_line_ctx.partner_id = partner_to_set

        # Create missing partner bank if necessary.
        if st_line.account_number and st_line.partner_id and not st_line.partner_bank_id:
            st_line_ctx.partner_bank_id = st_line._find_or_create_bank_account()

        # Refresh analytic lines.
        move.line_ids.analytic_line_ids.unlink()
        move.line_ids.with_context(validate_analytic=True)._create_analytic_lines()

    @contextmanager
    def _action_validate_method(self):
        self.ensure_one()
        st_line = self.st_line_id

        yield

        # The current record has been invalidated. Reload it completely.
        self.st_line_id = st_line
        self._ensure_loaded_lines()
        self.return_todo_command = {'done': True}

    def _js_action_validate(self):
        with self._action_validate_method():
            self._action_validate()

    def _action_to_check(self):
        self.st_line_id.move_id.to_check = True
        self.invalidate_recordset(fnames=['st_line_to_check'])
        self._action_validate()

    def _js_action_to_check(self):
        self.ensure_one()

        if self.state == 'valid':
            # The validation can be performed.
            with self._action_validate_method():
                self._action_to_check()
        else:
            # No need any validation.
            self.st_line_id.move_id.to_check = True
            self.invalidate_recordset(fnames=['st_line_to_check'])
            self.return_todo_command = {'done': True}

    def _js_action_reset(self):
        self.ensure_one()
        st_line = self.st_line_id
        st_line.action_undo_reconciliation()

        # The current record has been invalidated. Reload it completely.
        self.st_line_id = st_line
        self._ensure_loaded_lines()
        self._action_trigger_matching_rules()
        self.return_todo_command = {'done': True}

    def _js_action_set_as_checked(self):
        self.ensure_one()
        self.st_line_id.move_id.to_check = False
        self.invalidate_recordset(fnames=['st_line_to_check'])
        self.return_todo_command = {'done': True}

    def _action_clear_manual_operations_form(self):
        self.form_index = None

    def _action_remove_lines(self, lines):
        self.ensure_one()
        if not lines:
            return

        is_taxes_recomputation_needed = bool(lines.tax_ids)
        has_new_aml = any(line.flag == 'new_aml' for line in lines)

        # Update 'line_ids'.
        self.line_ids = [
            Command.unlink(line.id)
            for line in lines
        ]

        # Recompute taxes and auto balance the lines.
        if is_taxes_recomputation_needed:
            self._lines_recompute_taxes()
        if has_new_aml \
            and not self._lines_check_apply_early_payment_discount() \
            and not self._lines_check_apply_partial_matching():
            self._lines_recompute_exchange_diff()
        self._lines_add_auto_balance_line()
        self._action_clear_manual_operations_form()

    def _js_action_remove_line(self, line_index):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == line_index)
        self._action_remove_lines(line)

    def _action_select_reconcile_model(self, reco_model):
        self.ensure_one()

        # Cleanup a previously selected model.
        self.line_ids = [
            Command.unlink(x.id)
            for x in self.line_ids
            if x.flag not in ('new_aml', 'liquidity') and x.reconcile_model_id and x.reconcile_model_id != reco_model
        ]
        self._lines_recompute_taxes()

        # Compute the residual balance on which apply the newly selected model.
        auto_balance_line_vals = self._lines_prepare_auto_balance_line()
        residual_balance = auto_balance_line_vals['amount_currency']

        write_off_vals_list = reco_model._apply_lines_for_bank_widget(residual_balance, self.partner_id, self.st_line_id)

        # Apply the newly generated lines.
        self.line_ids = [
            Command.create(self._lines_prepare_reco_model_write_off_vals(reco_model, x))
            for x in write_off_vals_list
        ]

        self._lines_recompute_taxes()
        self._lines_add_auto_balance_line()

        if reco_model.to_check != self.st_line_to_check:
            self.st_line_id.move_id.to_check = reco_model.to_check
            self.invalidate_recordset(fnames=['st_line_to_check'])

    def _js_action_select_reconcile_model(self, reco_model_id):
        self.ensure_one()
        reco_model = self.env['account.reconcile.model'].browse(reco_model_id)
        self._action_select_reconcile_model(reco_model)

    def _action_add_new_amls(self, amls, reco_model=None, allow_partial=True):
        self.ensure_one()
        existing_amls = set(self.line_ids.source_aml_id)
        amls = amls.filtered(lambda x: x not in existing_amls)
        if not amls:
            return

        self._lines_load_new_amls(amls, reco_model=reco_model)
        self._lines_recompute_exchange_diff()
        if not self._lines_check_apply_early_payment_discount() and allow_partial:
            self._lines_check_apply_partial_matching()
        self._lines_add_auto_balance_line()
        self._action_clear_manual_operations_form()

    def _js_action_add_new_aml(self, aml_id):
        self.ensure_one()
        aml = self.env['account.move.line'].browse(aml_id)
        self._action_add_new_amls(aml)

    def _action_remove_new_amls(self, amls):
        self.ensure_one()
        to_remove = self.line_ids.filtered(lambda x: x.flag == 'new_aml' and x.source_aml_id in amls)
        self._action_remove_lines(to_remove)

    def _js_action_remove_new_aml(self, aml_id):
        self.ensure_one()
        aml = self.env['account.move.line'].browse(aml_id)
        self._action_remove_new_amls(aml)

    def _js_action_mount_line_in_edit(self, line_index):
        self.ensure_one()
        self.form_index = line_index

    def _js_action_line_changed(self, form_index, field_name):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == form_index)

        # Invalidate the cache of newly set value to force the recomputation of computed fields.
        value = line[field_name]
        line.invalidate_recordset(fnames=[field_name], flush=False)
        line[field_name] = value

        getattr(self, f'_line_value_changed_{field_name}')(line)

    def _js_action_line_set_partner_receivable_account(self, form_index):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == form_index)
        line.account_id = line.partner_receivable_account_id
        self._line_value_changed_account_id(line)

    def _js_action_line_set_partner_payable_account(self, form_index):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == form_index)
        line.account_id = line.partner_payable_account_id
        self._line_value_changed_account_id(line)

    def _js_action_redirect_to_move(self, form_index):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == form_index)
        move = line.source_aml_move_id

        action = {
            'type': 'ir.actions.act_window',
            'context': {'create': False},
            'view_mode': 'form',
        }

        if move.payment_id:
            action.update({
                'res_model': 'account.payment',
                'res_id': move.payment_id.id,
            })
        else:
            action.update({
                'res_model': 'account.move',
                'res_id': move.id,
            })
        self.return_todo_command = clean_action(action, self.env)

    def _js_action_apply_line_suggestion(self, form_index):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == form_index)

        # Since 'balance'/'amount_currency' are both dependencies of 'suggestion_balance'/'suggestion_amount_currency',
        # keep the value in variable before assigning anything to avoid an inconsistency after applying
        # 'suggestion_amount_currency' but before updating 'balance'.
        suggestion_amount_currency = line.suggestion_amount_currency
        suggestion_balance = line.suggestion_balance

        line.amount_currency = suggestion_amount_currency
        line.balance = suggestion_balance

        if line.currency_id == line.company_currency_id:
            self._line_value_changed_balance(line)
        else:
            self._line_value_changed_amount_currency(line)

    @api.model
    def collect_global_info_data(self, journal_id):
        journal = self.env['account.journal'].browse(journal_id)
        balance = ''
        if journal.exists() and any(company in journal.company_id._accessible_branches() for company in self.env.companies):
            balance = formatLang(self.env,
                                 journal.current_statement_balance,
                                 currency_obj=journal.currency_id or journal.company_id.sudo().currency_id)
        return {'balance_amount': balance}
