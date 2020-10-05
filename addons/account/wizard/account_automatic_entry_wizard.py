# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, formatLang

from collections import defaultdict
from itertools import groupby
from dateutil.relativedelta import relativedelta
import json


class AutomaticEntryWizard(models.TransientModel):
    _name = 'account.automatic.entry.wizard'
    _description = 'Create Automatic Entries'

    # General
    action = fields.Selection([('change_period', 'Change Period'), ('change_account', 'Change Account')], required=True)
    move_data = fields.Text(compute="_compute_move_data", help="JSON value of the moves to be created")
    preview_move_data = fields.Text(compute="_compute_preview_move_data", help="JSON value of the data to be displayed in the previewer")
    move_line_ids = fields.Many2many('account.move.line')
    company_id = fields.Many2one('res.company', required=True, readonly=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    total_amount = fields.Monetary(
        compute='_compute_from_move_line_ids',
        currency_field='company_currency_id',
        help="Total amount impacted by the automatic entry.")
    journal_id = fields.Many2one('account.journal', required=True, readonly=False, string="Journal",
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
        related="company_id.automatic_entry_default_journal_id",
        help="Journal where to create the entry.")

    # change period
    account_type = fields.Selection(
        selection=[('income', 'Revenue'), ('expense', 'Expense')],
        compute='_compute_from_move_line_ids')
    expense_accrual_account = fields.Many2one('account.account', readonly=False,
        domain="[('company_id', '=', company_id),"
               "('internal_type', 'not in', ('receivable', 'payable')),"
               "('is_off_balance', '=', False)]",
        related="company_id.expense_accrual_account_id")
    revenue_accrual_account = fields.Many2one('account.account', readonly=False,
        domain="[('company_id', '=', company_id),"
               "('internal_type', 'not in', ('receivable', 'payable')),"
               "('is_off_balance', '=', False)]",
        related="company_id.revenue_accrual_account_id")
    chg_period_date_from = fields.Date(
        string="Date from",
        default=lambda self: fields.Date.context_today(self),
        help="Date at which the smoothing of the balance will start.")
    chg_period_date_to = fields.Date(
        string="Date to",
        default=lambda self: fields.Date.context_today(self),
        help="Date at which the smoothing of the balance will end.")
    chg_period_time_division = fields.Boolean(
        string="Time Division",
        help="Allocate the balance to different periods considering their number of days.")
    chg_period_percentage = fields.Float(string="Percentage", default=100.0)
    chg_period_line_ids = fields.One2many(
        comodel_name='account.automatic.entry.wizard.line',
        inverse_name='wizard_id',
        string='Lines',
        store=True, readonly=False,
        compute='_compute_chg_period_line_ids')
    chg_period_warning_message = fields.Text(
        string="Warning",
        compute='_compute_chg_period_warning_message')

    # change account
    date = fields.Date(string="Transfer Date", default=lambda self: fields.Date.context_today(self))
    destination_account_id = fields.Many2one(string="To", comodel_name='account.account', help="Account to transfer to.")
    display_currency_helper = fields.Boolean(string="Currency Conversion Helper", compute='_compute_display_currency_helper',
        help="Technical field. Used to indicate whether or not to display the currency conversion tooltip. The tooltip informs a currency conversion will be performed with the transfer.")

    def _get_total_balance(self):
        self.ensure_one()
        return sum(line.amount_residual if line.account_id.reconcile else line.balance for line in self.move_line_ids)

    @api.depends('chg_period_date_from', 'chg_period_date_to', 'chg_period_time_division', 'chg_period_percentage')
    def _compute_chg_period_line_ids(self):
        ''' Create the lines representing the way the balance will be smoothed per period. '''
        for wizard in self:
            one2many_commands = [(5, 0)]

            date_from = wizard.chg_period_date_from
            date_to = wizard.chg_period_date_to
            percentage = (wizard.chg_period_percentage or 0.0) / 100.0

            if date_from and date_to and percentage:
                total_balance = wizard.company_currency_id.round(wizard._get_total_balance() * percentage)
                total_days = 0.0
                date_distribution = []
                while date_from <= date_to:
                    next_month_date = (date_from + relativedelta(months=1)).replace(day=1)
                    period_date = next_month_date - relativedelta(days=1)
                    period_days = (period_date - date_from).days
                    date_distribution.append((period_date, period_days))
                    date_from = next_month_date
                    total_days += period_days

                total_reported_balance = 0.0
                for period_date, nb_days in date_distribution:
                    if wizard.chg_period_time_division:
                        period_balance = wizard.company_currency_id.round(total_balance * nb_days / total_days)
                    else:
                        period_balance = wizard.company_currency_id.round(total_balance / len(date_distribution))
                    one2many_commands.append((0, 0, {
                        'wizard_id': wizard.id,
                        'date': period_date,
                        'balance': period_balance,
                    }))
                    total_reported_balance += period_balance

                # When the percentage is 100%, ensure the full balance is dispatched into the periods.
                # To avoid a huge gap in the last line, we ensure the rounding error is also smoothed.
                # For example: smoothing 100 into 12 months:
                # 12 lines of 8.33 are generated at this point. Since 8.33 * 12 = 99.96, the error of 0.04 will be
                # smoothed by adding 0.01 to the last 4 periods.
                if wizard.chg_period_percentage == 100.0:
                    total_rounding_error = wizard.company_currency_id.round(total_balance - total_reported_balance)
                    nber_rounding_steps = int(abs(total_rounding_error / wizard.company_currency_id.rounding))
                    rounding_error = round(
                        nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0,
                        wizard.company_currency_id.decimal_places,
                    )
                    nber_periods = len(one2many_commands) - 1
                    if len(one2many_commands) > nber_rounding_steps:
                        for i in range(nber_rounding_steps):
                            one2many_commands[nber_periods - i][2]['balance'] += rounding_error

            wizard.chg_period_line_ids = one2many_commands

    @api.depends('chg_period_date_from', 'chg_period_date_to')
    def _compute_chg_period_warning_message(self):
        for wizard in self:
            if wizard.chg_period_date_from and wizard.chg_period_date_to and wizard.chg_period_date_from > wizard.chg_period_date_to:
                wizard.chg_period_warning_message = _("Check the dates. The period cannot start later than its own end.")
            else:
                wizard.chg_period_warning_message = False

    @api.depends('move_line_ids.balance')
    def _compute_from_move_line_ids(self):
        for wizard in self:
            wizard.total_amount = wizard._get_total_balance()
            wizard.account_type = 'income' if wizard.total_amount < 0.0 else 'expense'

    @api.depends('destination_account_id')
    def _compute_display_currency_helper(self):
        for record in self:
            record.display_currency_helper = bool(record.destination_account_id.currency_id)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not set(fields) & set(['move_line_ids', 'company_id']):
            return res

        if self.env.context.get('active_model') != 'account.move.line' or not self.env.context.get('active_ids'):
            raise UserError(_('This can only be used on journal items'))
        move_line_ids = self.env['account.move.line'].browse(self.env.context['active_ids'])
        res['move_line_ids'] = [(6, 0, move_line_ids.ids)]

        if any(move.state != 'posted' for move in move_line_ids.mapped('move_id')):
            raise UserError(_('You can only change the period/account for posted journal items.'))
        if any(move_line.reconciled for move_line in move_line_ids):
            raise UserError(_('You can only change the period/account for items that are not yet reconciled.'))
        if any(line.company_id != move_line_ids[0].company_id for line in move_line_ids):
            raise UserError(_('You cannot use this wizard on journal entries belonging to different companies.'))
        res['company_id'] = move_line_ids[0].company_id.id

        allowed_actions = set(dict(self._fields['action'].selection))
        if self.env.context.get('default_action'):
            allowed_actions = {self.env.context['default_action']}
        if any(line.account_id.user_type_id != move_line_ids[0].account_id.user_type_id for line in move_line_ids):
            allowed_actions.discard('change_period')
        if not allowed_actions:
            raise UserError(_('No possible action found with the selected lines.'))
        res['action'] = allowed_actions.pop()
        return res

    def _get_move_dict_vals_change_account(self):
        line_vals = []

        # Group data from selected move lines
        counterpart_balances = defaultdict(lambda: defaultdict(lambda: 0))
        grouped_source_lines = defaultdict(lambda: self.env['account.move.line'])

        for line in self.move_line_ids.filtered(lambda x: x.account_id != self.destination_account_id):
            counterpart_currency = line.currency_id
            counterpart_amount_currency = line.amount_currency

            if self.destination_account_id.currency_id and self.destination_account_id.currency_id != self.company_id.currency_id:
                counterpart_currency = self.destination_account_id.currency_id
                counterpart_amount_currency = self.company_id.currency_id._convert(line.balance, self.destination_account_id.currency_id, self.company_id, line.date)

            counterpart_balances[(line.partner_id, counterpart_currency)]['amount_currency'] += counterpart_amount_currency
            counterpart_balances[(line.partner_id, counterpart_currency)]['balance'] += line.balance
            grouped_source_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        # Generate counterpart lines' vals
        for (counterpart_partner, counterpart_currency), counterpart_vals in counterpart_balances.items():
            source_accounts = self.move_line_ids.mapped('account_id')
            counterpart_label = len(source_accounts) == 1 and _("Transfer from %s", source_accounts.display_name) or _("Transfer counterpart")

            if not counterpart_currency.is_zero(counterpart_vals['amount_currency']):
                line_vals.append({
                    'name': counterpart_label,
                    'debit': counterpart_vals['balance'] > 0 and self.company_id.currency_id.round(counterpart_vals['balance']) or 0,
                    'credit': counterpart_vals['balance'] < 0 and self.company_id.currency_id.round(-counterpart_vals['balance']) or 0,
                    'account_id': self.destination_account_id.id,
                    'partner_id': counterpart_partner.id or None,
                    'amount_currency': counterpart_currency.round((counterpart_vals['balance'] < 0 and -1 or 1) * abs(counterpart_vals['amount_currency'])) or 0,
                    'currency_id': counterpart_currency.id,
                })

        # Generate change_account lines' vals
        for (partner, currency, account), lines in grouped_source_lines.items():
            account_balance = sum(line.balance for line in lines)
            if not self.company_id.currency_id.is_zero(account_balance):
                account_amount_currency = currency.round(sum(line.amount_currency for line in lines))
                line_vals.append({
                    'name': _('Transfer to %s', self.destination_account_id.display_name or _('[Not set]')),
                    'debit': account_balance < 0 and self.company_id.currency_id.round(-account_balance) or 0,
                    'credit': account_balance > 0 and self.company_id.currency_id.round(account_balance) or 0,
                    'account_id': account.id,
                    'partner_id': partner.id or None,
                    'currency_id': currency.id,
                    'amount_currency': (account_balance > 0 and -1 or 1) * abs(account_amount_currency),
                })

        return [{
            'currency_id': self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id,
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': fields.Date.to_string(self.date),
            'ref': self.destination_account_id.display_name and _("Transfer entry to %s", self.destination_account_id.display_name or ''),
            'line_ids': [(0, 0, line) for line in line_vals],
        }]

    def _get_move_dict_vals_change_period(self):
        # set the change_period account on the selected journal items
        accrual_account = self.revenue_accrual_account if self.account_type == 'income' else self.expense_accrual_account
        total_percentage = sum(self.chg_period_line_ids.mapped('percentage'))

        move_data = {
            'original_dates': {},
            'new_dates': {},
        }

        # ==== Prepare journal entries (account.move) ====

        for date, grouped_lines in groupby(self.move_line_ids, lambda line: line.date):
            grouped_lines = list(grouped_lines)
            amount = sum(l.balance for l in grouped_lines)
            move_data['original_dates'][date] = {
                'move_type': 'entry',
                'ref': self._format_strings(_('Adjusting Entry of {date} ({percent:f}% recognized on {new_date})'), grouped_lines[0].move_id, amount),
                'date': fields.Date.to_string(date),
                'journal_id': self.journal_id.id,
                'line_ids': [],
            }

        for line in self.chg_period_line_ids:
            ref = _("Adjusting Entry made on {date} ({percent:f}%)").format(
                date=format_date(self.env, line.date),
                percent=line.percentage,
            )
            move_data['new_dates'][line.date] = {
                'move_type': 'entry',
                'ref': ref,
                'date': fields.Date.to_string(line.date),
                'journal_id': self.journal_id.id,
                'line_ids': [],
            }

        # ==== Prepare journal items (account.move.line) ====

        for aml in self.move_line_ids:

            total_reported_balance = 0.0
            total_reported_amount_currency = 0.0

            # Avoid rounding issues with 100%.
            if round(total_percentage, 2) == 100.0:
                total_balance_to_report = aml.balance
                total_amount_currency_to_report = aml.amount_currency
            else:
                total_balance_to_report = aml.company_currency_id.round((total_percentage / 100) * aml.balance)
                total_amount_currency_to_report = aml.currency_id.round((total_percentage / 100) * aml.amount_currency)

            for i, line in enumerate(self.chg_period_line_ids):
                # Avoid rounding issue on the last line.
                if i == len(self.chg_period_line_ids) - 1:
                    reported_balance = total_balance_to_report - total_reported_balance
                    reported_amount_currency = total_amount_currency_to_report - total_reported_amount_currency
                else:
                    reported_balance = aml.company_currency_id.round((line.percentage / 100) * aml.balance)
                    reported_amount_currency = aml.currency_id.round((line.percentage / 100) * aml.amount_currency)

                total_reported_balance += reported_balance
                total_reported_amount_currency += reported_amount_currency

                move_data['new_dates'][line.date]['line_ids'] += [
                    (0, 0, {
                        'name': aml.name or '',
                        'currency_id': aml.currency_id.id,
                        'account_id': aml.account_id.id,
                        'partner_id': aml.partner_id.id,
                        'debit': reported_balance if reported_balance > 0.0 else 0.0,
                        'credit': -reported_balance if reported_balance < 0.0 else 0.0,
                        'amount_currency': reported_amount_currency,
                    }),
                    (0, 0, {
                        'name': _('Adjusting Entry'),
                        'currency_id': aml.currency_id.id,
                        'account_id': accrual_account.id,
                        'partner_id': aml.partner_id.id,
                        'debit': -reported_balance if reported_balance < 0.0 else 0.0,
                        'credit': reported_balance if reported_balance > 0.0 else 0.0,
                        'amount_currency': -reported_amount_currency,
                    }),
                ]

            move_data['original_dates'][aml.date]['line_ids'] += [
                (0, 0, {
                    'name': aml.name or '',
                    'currency_id': aml.currency_id.id,
                    'account_id': aml.account_id.id,
                    'partner_id': aml.partner_id.id,
                    'debit': -total_reported_balance if total_reported_balance < 0.0 else 0.0,
                    'credit': total_reported_balance if total_reported_balance > 0.0 else 0.0,
                    'amount_currency': -total_reported_amount_currency,
                }),
                (0, 0, {
                    'name': _('Adjusting Entry'),
                    'currency_id': aml.currency_id.id,
                    'account_id': accrual_account.id,
                    'partner_id': aml.partner_id.id,
                    'debit': total_reported_balance if total_reported_balance > 0.0 else 0.0,
                    'credit': -total_reported_balance if total_reported_balance < 0.0 else 0.0,
                    'amount_currency': total_reported_amount_currency,
                }),
            ]

        return list(move_data['original_dates'].values()) + list(move_data['new_dates'].values())

    @api.depends('move_line_ids', 'journal_id', 'revenue_accrual_account', 'expense_accrual_account',
                 'date', 'account_type', 'action', 'destination_account_id',
                 'chg_period_line_ids')
    def _compute_move_data(self):
        for record in self:
            if record.action == 'change_period':
                if any(line.account_id.user_type_id != record.move_line_ids[0].account_id.user_type_id for line in record.move_line_ids):
                    raise UserError(_('All accounts on the lines must be of the same type.'))
            if record.action == 'change_period':
                record.move_data = json.dumps(record._get_move_dict_vals_change_period())
            elif record.action == 'change_account':
                record.move_data = json.dumps(record._get_move_dict_vals_change_account())

    @api.depends('move_data')
    def _compute_preview_move_data(self):
        for record in self:
            preview_columns = [
                {'field': 'account_id', 'label': _('Account')},
                {'field': 'name', 'label': _('Label')},
                {'field': 'debit', 'label': _('Debit'), 'class': 'text-right text-nowrap'},
                {'field': 'credit', 'label': _('Credit'), 'class': 'text-right text-nowrap'},
            ]
            if record.action == 'change_account':
                preview_columns[2:2] = [{'field': 'partner_id', 'label': _('Partner')}]

            move_vals = json.loads(record.move_data)
            preview_vals = []
            for move in move_vals[:4]:
                preview_vals += [self.env['account.move']._move_dict_to_preview_vals(move, record.company_id.currency_id)]
            preview_discarded = max(0, len(move_vals) - len(preview_vals))

            record.preview_move_data = json.dumps({
                'groups_vals': preview_vals,
                'options': {
                    'discarded_number': _("%d moves", preview_discarded) if preview_discarded else False,
                    'columns': preview_columns,
                },
            })

    def do_action(self):
        move_vals = json.loads(self.move_data)
        if self.action == 'change_period':
            return self._do_action_change_period(move_vals)
        elif self.action == 'change_account':
            return self._do_action_change_account(move_vals)

    def _do_action_change_period(self, move_vals):
        accrual_account = self.revenue_accrual_account if self.account_type == 'income' else self.expense_accrual_account

        # ==== Create new journal entries ====

        created_moves = self.env['account.move'].create(move_vals)
        created_moves._post()

        # ==== Manage chatters ====

        destination_move = created_moves[0]
        accrual_moves = created_moves[1:]

        messages_from = [_("<li>%(link)s</li>", link=self._format_move_link(move)) for move in self.move_line_ids.move_id]
        messages_from = ''.join([_("Adjusting Entry generated for these journal entries:<ul>")] + messages_from + ["</ul>"])

        messages_to = [_("Adjusting Entries created:<ul>")]
        messages_to.append(self._format_strings(
            _("<li>%(link)s cancelling {percent:f}%% of {amount}</li>", link=self._format_move_link(destination_move)),
            destination_move, self.total_amount,
        ))
        for accrual_move in accrual_moves:
            messages_to.append(self._format_strings(
                _("<li>%(link)s postponing it to {new_date}</li>", link=self._format_move_link(accrual_move)),
                accrual_move, 0.0,
            ))
        messages_to = ''.join(messages_to + ["</ul>"])

        for move in self.move_line_ids.move_id:
            move.message_post(body=messages_to)
        destination_move.message_post(body=messages_from)
        for accrual_move in accrual_moves:
            accrual_move.message_post(body=messages_from)

        # ==== Reconcile ====

        if accrual_account.reconcile and all(move.state == 'posted' for move in created_moves):
            created_moves.line_ids.filtered(lambda line: line.account_id == accrual_account and not line.reconciled).reconcile()

        # ==== Redirect ====

        action = {
            'name': _('Generated Entries'),
            'domain': [('id', 'in', created_moves.ids)],
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
        }
        if len(created_moves) == 1:
            action.update({'view_mode': 'form', 'res_id': created_moves.id})
        return action

    def _do_action_change_account(self, move_vals):
        new_move = self.env['account.move'].create(move_vals)
        new_move._post()

        # Group lines
        grouped_lines = defaultdict(lambda: self.env['account.move.line'])
        destination_lines = self.move_line_ids.filtered(lambda x: x.account_id == self.destination_account_id)
        for line in self.move_line_ids - destination_lines:
            grouped_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        # Reconcile
        for (partner, currency, account), lines in grouped_lines.items():
            if account.reconcile:
                to_reconcile = lines + new_move.line_ids.filtered(lambda x: x.account_id == account and x.partner_id == partner and x.currency_id == currency)
                to_reconcile.reconcile()

            if destination_lines and self.destination_account_id.reconcile:
                to_reconcile = destination_lines + new_move.line_ids.filtered(lambda x: x.account_id == self.destination_account_id and x.partner_id == partner and x.currency_id == currency)
                to_reconcile.reconcile()

        # Log the operation on source moves
        acc_transfer_per_move = defaultdict(lambda: defaultdict(lambda: 0))  # dict(move, dict(account, balance))
        for line in self.move_line_ids:
            acc_transfer_per_move[line.move_id][line.account_id] += line.balance

        for move, balances_per_account in acc_transfer_per_move.items():
            message_to_log = self._format_transfer_source_log(balances_per_account, new_move)
            if message_to_log:
                move.message_post(body=message_to_log)

        # Log on target move as well
        new_move.message_post(body=self._format_new_transfer_move_log(acc_transfer_per_move))

        return {
            'name': _("Transfer"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': new_move.id,
        }

    # Transfer utils
    def _format_new_transfer_move_log(self, acc_transfer_per_move):
        format = _("<li>{amount} ({debit_credit}) from {link}, <strong>%(account_source_name)s</strong></li>")
        rslt = _("This entry transfers the following amounts to <strong>%(destination)s</strong> <ul>", destination=self.destination_account_id.display_name)
        for move, balances_per_account in acc_transfer_per_move.items():
            for account, balance in balances_per_account.items():
                if account != self.destination_account_id:  # Otherwise, logging it here is confusing for the user
                    rslt += self._format_strings(format, move, balance) % {'account_source_name': account.display_name}

        rslt += '</ul>'
        return rslt

    def _format_transfer_source_log(self, balances_per_account, transfer_move):
        transfer_format = _("<li>{amount} ({debit_credit}) from <strong>%s</strong> were transferred to <strong>{account_target_name}</strong> by {link}</li>")
        content = ''
        for account, balance in balances_per_account.items():
            if account != self.destination_account_id:
                content += self._format_strings(transfer_format, transfer_move, balance) % account.display_name
        return content and '<ul>' + content + '</ul>' or None

    def _format_move_link(self, move):
        move_link_format = "<a href=# data-oe-model=account.move data-oe-id={move_id}>{move_name}</a>"
        return move_link_format.format(move_id=move.id, move_name=move.name)

    def _format_strings(self, string, move, amount):
        return string.format(
            percent=sum(self.chg_period_line_ids.mapped('percentage')),
            name=move.name,
            id=move.id,
            amount=formatLang(self.env, abs(amount), currency_obj=self.company_id.currency_id),
            debit_credit=amount < 0 and _('C') or _('D'),
            link=self._format_move_link(move),
            date=format_date(self.env, move.date),
            new_date=self.date and format_date(self.env, self.date) or _('[Not set]'),
            account_target_name=self.destination_account_id.display_name,
        )


class AutomaticEntryWizardLine(models.TransientModel):
    _name = "account.automatic.entry.wizard.line"
    _description = "Create Automatic Entries Line"

    wizard_id = fields.Many2one(
        comodel_name='account.automatic.entry.wizard',
        required=True, readonly=True, ondelete='cascade')
    date = fields.Date(
        string="Date",
        required=True,
        default=lambda self: fields.Date.context_today(self))
    percentage = fields.Float(
        string="Percentage",
        store=True, readonly=False,
        compute='_compute_percentage',
        help="Percentage of each line to execute the action on.")
    balance = fields.Monetary(
        string="Amount",
        store=True, readonly=False,
        compute='_compute_balance',
        currency_field='company_currency_id',
        help="Total amount impacted by the automatic entry.")

    # ==== Display purpose fields ====
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='wizard_id.company_id.currency_id')

    @api.depends('balance')
    def _compute_percentage(self):
        for line in self:
            total = abs(line.wizard_id._get_total_balance())
            line.percentage = total and (abs(line.balance) / total) * 100.0 or 0.0

    @api.depends('percentage')
    def _compute_balance(self):
        for line in self:
            line.balance = line.company_currency_id.round((line.percentage / 100.0) * line.wizard_id._get_total_balance())
