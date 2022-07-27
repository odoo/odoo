# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, html2plaintext
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import get_unaccent_wrapper
from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountCashboxLine(models.Model):
    """ Cash Box Details """
    _name = 'account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'coin_value'
    _order = 'coin_value'

    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        for cashbox_line in self:
            cashbox_line.subtotal = cashbox_line.coin_value * cashbox_line.number

    coin_value = fields.Float(string='Coin/Bill Value', required=True, digits=0)
    number = fields.Integer(string='#Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox")
    currency_id = fields.Many2one('res.currency', related='cashbox_id.currency_id')


class AccountBankStmtCashWizard(models.Model):
    """
    Account Bank Statement popup that allows entering cash details.
    """
    _name = 'account.bank.statement.cashbox'
    _description = 'Bank Statement Cashbox'
    _rec_name = 'id'

    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'cashbox_id', string='Cashbox Lines')
    start_bank_stmt_ids = fields.One2many('account.bank.statement', 'cashbox_start_id')
    end_bank_stmt_ids = fields.One2many('account.bank.statement', 'cashbox_end_id')
    total = fields.Float(compute='_compute_total')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency')

    @api.depends('start_bank_stmt_ids', 'end_bank_stmt_ids')
    def _compute_currency(self):
        for cashbox in self:
            cashbox.currency_id = False
            if cashbox.end_bank_stmt_ids:
                cashbox.currency_id = cashbox.end_bank_stmt_ids[0].currency_id
            if cashbox.start_bank_stmt_ids:
                cashbox.currency_id = cashbox.start_bank_stmt_ids[0].currency_id

    @api.depends('cashbox_lines_ids', 'cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number')
    def _compute_total(self):
        for cashbox in self:
            cashbox.total = sum([line.subtotal for line in cashbox.cashbox_lines_ids])

    @api.model
    def default_get(self, fields):
        vals = super(AccountBankStmtCashWizard, self).default_get(fields)
        balance = self.env.context.get('balance')
        statement_id = self.env.context.get('statement_id')
        if 'start_bank_stmt_ids' in fields and not vals.get('start_bank_stmt_ids') and statement_id and balance == 'start':
            vals['start_bank_stmt_ids'] = [(6, 0, [statement_id])]
        if 'end_bank_stmt_ids' in fields and not vals.get('end_bank_stmt_ids') and statement_id and balance == 'close':
            vals['end_bank_stmt_ids'] = [(6, 0, [statement_id])]

        return vals

    def name_get(self):
        result = []
        for cashbox in self:
            result.append((cashbox.id, str(cashbox.total)))
        return result

    @api.model_create_multi
    def create(self, vals):
        cashboxes = super(AccountBankStmtCashWizard, self).create(vals)
        cashboxes._validate_cashbox()
        return cashboxes

    def write(self, vals):
        res = super(AccountBankStmtCashWizard, self).write(vals)
        self._validate_cashbox()
        return res

    def _validate_cashbox(self):
        for cashbox in self:
            if cashbox.start_bank_stmt_ids:
                cashbox.start_bank_stmt_ids.write({'balance_start': cashbox.total})
            if cashbox.end_bank_stmt_ids:
                cashbox.end_bank_stmt_ids.write({'balance_end_real': cashbox.total})


class AccountBankStmtCloseCheck(models.TransientModel):
    """
    Account Bank Statement wizard that check that closing balance is correct.
    """
    _name = 'account.bank.statement.closebalance'
    _description = 'Bank Statement Closing Balance'

    def validate(self):
        bnk_stmt_id = self.env.context.get('active_id', False)
        if bnk_stmt_id:
            self.env['account.bank.statement'].browse(bnk_stmt_id).button_validate()
        return {'type': 'ir.actions.act_window_close'}


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "date desc, name desc, id desc"
    _inherit = ['mail.thread', 'sequence.mixin']
    _check_company_auto = True
    _sequence_index = "journal_id"

    # Note: the reason why we did 2 separate function with the same dependencies (one for balance_start and one for balance_end_real)
    # is because if we create a bank statement with a default value for one of the field but not the other, the compute method
    # won't be called and therefore the other field will have a value of 0 and we don't want that.
    @api.depends('previous_statement_id', 'previous_statement_id.balance_end_real')
    def _compute_starting_balance(self):
        for statement in self:
            if statement.previous_statement_id.balance_end_real != statement.balance_start:
                statement.balance_start = statement.previous_statement_id.balance_end_real
            else:
                # Need default value
                statement.balance_start = statement.balance_start or 0.0

    @api.depends('previous_statement_id', 'previous_statement_id.balance_end_real')
    def _compute_ending_balance(self):
        latest_statement = self.env['account.bank.statement'].search([('journal_id', '=', self[0].journal_id.id)], limit=1)
        for statement in self:
            # recompute balance_end_real in case we are in a bank journal and if we change the
            # balance_end_real of previous statement as we don't want
            # holes in case we add a statement in between 2 others statements.
            # We only do this for the bank journal as we use the balance_end_real in cash
            # journal for verification and creating cash difference entries so we don't want
            # to recompute the value in that case
            if statement.journal_type == 'bank':
                # If we are on last statement and that statement already has a balance_end_real, don't change the balance_end_real
                # Otherwise, recompute balance_end_real to prevent holes between statement.
                if latest_statement.id and statement.id == latest_statement.id and not float_is_zero(statement.balance_end_real, precision_digits=statement.currency_id.decimal_places):
                    statement.balance_end_real = statement.balance_end_real or 0.0
                else:
                    total_entry_encoding = sum([line.amount for line in statement.line_ids])
                    statement.balance_end_real = statement.previous_statement_id.balance_end_real + total_entry_encoding
            else:
                # Need default value
                statement.balance_end_real = statement.balance_end_real or 0.0

    @api.depends('line_ids', 'balance_start', 'line_ids.amount', 'balance_end_real')
    def _end_balance(self):
        for statement in self:
            statement.total_entry_encoding = sum([line.amount for line in statement.line_ids])
            statement.balance_end = statement.balance_start + statement.total_entry_encoding
            statement.difference = statement.balance_end_real - statement.balance_end

    def _is_difference_zero(self):
        for bank_stmt in self:
            bank_stmt.is_difference_zero = float_is_zero(bank_stmt.difference, precision_digits=bank_stmt.currency_id.decimal_places)

    @api.depends('journal_id')
    def _compute_currency(self):
        for statement in self:
            statement.currency_id = statement.journal_id.currency_id or statement.company_id.currency_id

    @api.depends('move_line_ids')
    def _get_move_line_count(self):
        for statement in self:
            statement.move_line_count = len(statement.move_line_ids)

    @api.model
    def _default_journal(self):
        journal_type = self.env.context.get('journal_type', False)
        company_id = self.env.company.id
        if journal_type:
            return self.env['account.journal'].search([
                ('type', '=', journal_type),
                ('company_id', '=', company_id)
            ], limit=1)
        return self.env['account.journal']

    @api.depends('balance_start', 'previous_statement_id')
    def _compute_is_valid_balance_start(self):
        for bnk in self:
            bnk.is_valid_balance_start = (
                bnk.currency_id.is_zero(
                    bnk.balance_start - bnk.previous_statement_id.balance_end_real
                )
                if bnk.previous_statement_id
                else True
            )

    @api.depends('date', 'journal_id')
    def _get_previous_statement(self):
        for st in self:
            # Search for the previous statement
            domain = [('date', '<=', st.date), ('journal_id', '=', st.journal_id.id)]
            # The reason why we have to perform this test is because we have two use case here:
            # First one is in case we are creating a new record, in that case that new record does
            # not have any id yet. However if we are updating an existing record, the domain date <= st.date
            # will find the record itself, so we have to add a condition in the search to ignore self.id
            if not isinstance(st.id, models.NewId):
                domain.extend(['|', '&', ('id', '<', st.id), ('date', '=', st.date), '&', ('id', '!=', st.id), ('date', '!=', st.date)])
            previous_statement = self.search(domain, limit=1, order='date desc, id desc')
            st.previous_statement_id = previous_statement.id

    name = fields.Char(string='Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True)
    reference = fields.Char(string='External Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True, help="Used to hold the reference of the external mean that created this statement (name of imported file, reference of online synchronization...)")
    date = fields.Date(required=True, states={'confirm': [('readonly', True)]}, index=True, copy=False, default=fields.Date.context_today)
    date_done = fields.Datetime(string="Closed On")
    balance_start = fields.Monetary(string='Starting Balance', states={'confirm': [('readonly', True)]}, compute='_compute_starting_balance', readonly=False, store=True, tracking=True)
    balance_end_real = fields.Monetary('Ending Balance', states={'confirm': [('readonly', True)]}, compute='_compute_ending_balance', recursive=True, readonly=False, store=True, tracking=True)
    state = fields.Selection(string='Status', required=True, readonly=True, copy=False, tracking=True, selection=[
            ('open', 'New'),
            ('posted', 'Processing'),
            ('confirm', 'Validated'),
        ], default='open',
        help="The current state of your bank statement:"
             "- New: Fully editable with draft Journal Entries."
             "- Processing: No longer editable with posted Journal entries, ready for the reconciliation."
             "- Validated: All lines are reconciled. There is nothing left to process.")
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'confirm': [('readonly', True)]}, default=_default_journal, check_company=True)
    journal_type = fields.Selection(related='journal_id.type', help="Technical field used for usability purposes")
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True)

    total_entry_encoding = fields.Monetary('Transactions Subtotal', compute='_end_balance', store=True, help="Total of transaction lines.")
    balance_end = fields.Monetary('Computed Balance', compute='_end_balance', store=True, help='Balance as calculated based on Opening Balance and transaction lines')
    difference = fields.Monetary(compute='_end_balance', store=True, help="Difference between the computed ending balance and the specified ending balance.")

    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines', states={'confirm': [('readonly', True)]}, copy=True)
    move_line_ids = fields.One2many('account.move.line', 'statement_id', string='Entry lines', states={'confirm': [('readonly', True)]})
    move_line_count = fields.Integer(compute="_get_move_line_count")

    all_lines_reconciled = fields.Boolean(compute='_compute_all_lines_reconciled',
        help="Technical field indicating if all statement lines are fully reconciled.")
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    cashbox_start_id = fields.Many2one('account.bank.statement.cashbox', string="Starting Cashbox")
    cashbox_end_id = fields.Many2one('account.bank.statement.cashbox', string="Ending Cashbox")
    is_difference_zero = fields.Boolean(compute='_is_difference_zero', string='Is zero', help="Check if difference is zero.")
    previous_statement_id = fields.Many2one('account.bank.statement', help='technical field to compute starting balance correctly', compute='_get_previous_statement', store=True)
    is_valid_balance_start = fields.Boolean(string="Is Valid Balance Start", store=True,
        compute="_compute_is_valid_balance_start",
        help="Technical field to display a warning message in case starting balance is different than previous ending balance")
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    def write(self, values):
        res = super(AccountBankStatement, self).write(values)
        if values.get('date') or values.get('journal'):
            # If we are changing the date or journal of a bank statement, we have to change its previous_statement_id. This is done
            # automatically using the compute function, but we also have to change the previous_statement_id of records that were
            # previously pointing toward us and records that were pointing towards our new previous_statement_id. This is done here
            # by marking those record as needing to be recomputed.
            # Note that marking the field is not enough as we also have to recompute all its other fields that are depending on 'previous_statement_id'
            # hence the need to call modified afterwards.
            to_recompute = self.search([('previous_statement_id', 'in', self.ids), ('id', 'not in', self.ids), ('journal_id', 'in', self.mapped('journal_id').ids)])
            if to_recompute:
                self.env.add_to_compute(self._fields['previous_statement_id'], to_recompute)
                to_recompute.modified(['previous_statement_id'])
            next_statements_to_recompute = self.search([('previous_statement_id', 'in', [st.previous_statement_id.id for st in self]), ('id', 'not in', self.ids), ('journal_id', 'in', self.mapped('journal_id').ids)])
            if next_statements_to_recompute:
                self.env.add_to_compute(self._fields['previous_statement_id'], next_statements_to_recompute)
                next_statements_to_recompute.modified(['previous_statement_id'])
        return res

    @api.model_create_multi
    def create(self, values):
        res = super(AccountBankStatement, self).create(values)
        # Upon bank stmt creation, it is possible that the statement is inserted between two other statements and not at the end
        # In that case, we have to search for statement that are pointing to the same previous_statement_id as ourselve in order to
        # change their previous_statement_id to us. This is done by marking the field 'previous_statement_id' to be recomputed for such records.
        # Note that marking the field is not enough as we also have to recompute all its other fields that are depending on 'previous_statement_id'
        # hence the need to call modified afterwards.
        # The reason we are doing this here and not in a compute field is that it is not easy to write dependencies for such field.
        next_statements_to_recompute = self.search([('previous_statement_id', 'in', [st.previous_statement_id.id for st in res]), ('id', 'not in', res.ids), ('journal_id', 'in', res.journal_id.ids)])
        if next_statements_to_recompute:
            self.env.add_to_compute(self._fields['previous_statement_id'], next_statements_to_recompute)
            next_statements_to_recompute.modified(['previous_statement_id'])
        return res

    @api.depends('line_ids.is_reconciled')
    def _compute_all_lines_reconciled(self):
        for statement in self:
            statement.all_lines_reconciled = all(st_line.is_reconciled for st_line in statement.line_ids)

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        for st_line in self.line_ids:
            st_line.journal_id = self.journal_id
            st_line.currency_id = self.journal_id.currency_id or self.company_id.currency_id

    def _check_balance_end_real_same_as_computed(self):
        """ Check the balance_end_real (encoded manually by the user) is equals to the balance_end (computed by odoo). """
        return self._check_cash_balance_end_real_same_as_computed() and self._check_bank_balance_end_real_same_as_computed()

    def _check_cash_balance_end_real_same_as_computed(self):
        """ Check the balance_end_real (encoded manually by the user) is equals to the balance_end (computed by odoo).
            For a cash statement, if there is a difference, the different is set automatically to a profit/loss account.
        """
        for statement in self.filtered(lambda stmt: stmt.journal_type == 'cash'):
            if not statement.currency_id.is_zero(statement.difference):
                st_line_vals = {
                    'statement_id': statement.id,
                    'journal_id': statement.journal_id.id,
                    'amount': statement.difference,
                    'date': statement.date,
                }

                if statement.currency_id.compare_amounts(statement.difference, 0.0) < 0.0:
                    if not statement.journal_id.loss_account_id:
                        raise UserError(_(
                            "Please go on the %s journal and define a Loss Account. "
                            "This account will be used to record cash difference.",
                            statement.journal_id.name
                        ))

                    st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Loss)")
                    st_line_vals['counterpart_account_id'] = statement.journal_id.loss_account_id.id
                else:
                    # statement.difference > 0.0
                    if not statement.journal_id.profit_account_id:
                        raise UserError(_(
                            "Please go on the %s journal and define a Profit Account. "
                            "This account will be used to record cash difference.",
                            statement.journal_id.name
                        ))

                    st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Profit)")
                    st_line_vals['counterpart_account_id'] = statement.journal_id.profit_account_id.id

                self.env['account.bank.statement.line'].create(st_line_vals)
        return True

    def _check_bank_balance_end_real_same_as_computed(self):
        """ Check the balance_end_real (encoded manually by the user) is equals to the balance_end (computed by odoo). """
        for statement in self.filtered(lambda stmt: stmt.journal_type == 'bank'):
            if not statement.currency_id.is_zero(statement.difference):
                balance_end_real = formatLang(self.env, statement.balance_end_real, currency_obj=statement.currency_id)
                balance_end = formatLang(self.env, statement.balance_end, currency_obj=statement.currency_id)
                raise UserError(_(
                    'The ending balance is incorrect !\nThe expected balance (%(real_balance)s) is different from the computed one (%(computed_balance)s).',
                    real_balance=balance_end_real,
                    computed_balance=balance_end
                ))
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_only_if_open(self):
        for statement in self:
            if statement.state != 'open':
                raise UserError(_('In order to delete a bank statement, you must first cancel it to delete related journal items.'))

    def unlink(self):
        for statement in self:
            # Explicitly unlink bank statement lines so it will check that the related journal entries have been deleted first
            statement.line_ids.unlink()
            # Some other bank statements might be link to this one, so in that case we have to switch the previous_statement_id
            # from that statement to the one linked to this statement
            next_statement = self.search([('previous_statement_id', '=', statement.id), ('journal_id', '=', statement.journal_id.id)])
            if next_statement:
                next_statement.previous_statement_id = statement.previous_statement_id
        return super(AccountBankStatement, self).unlink()

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('journal_id')
    def _check_journal(self):
        for statement in self:
            if any(st_line.journal_id != statement.journal_id for st_line in statement.line_ids):
                raise ValidationError(_('The journal of a bank statement line must always be the same as the bank statement one.'))

    def _constrains_date_sequence(self):
        # Multiple import methods set the name to things that are not sequences:
        # i.e. Statement from {date1} to {date2}
        # It makes this constraint not applicable, and it is less needed on bank statements as it
        # is only an indication and not some thing legal.
        return

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def open_cashbox_id(self):
        self.ensure_one()
        context = dict(self.env.context or {})
        if context.get('balance'):
            context['statement_id'] = self.id
            if context['balance'] == 'start':
                cashbox_id = self.cashbox_start_id.id
            elif context['balance'] == 'close':
                cashbox_id = self.cashbox_end_id.id
            else:
                cashbox_id = False

            action = {
                'name': _('Cash Control'),
                'view_mode': 'form',
                'res_model': 'account.bank.statement.cashbox',
                'view_id': self.env.ref('account.view_account_bnk_stmt_cashbox_footer').id,
                'type': 'ir.actions.act_window',
                'res_id': cashbox_id,
                'context': context,
                'target': 'new'
            }

            return action

    def button_post(self):
        ''' Move the bank statements from 'draft' to 'posted'. '''
        if any(statement.state != 'open' for statement in self):
            raise UserError(_("Only new statements can be posted."))

        self._check_cash_balance_end_real_same_as_computed()

        for statement in self:
            if not statement.name:
                statement._set_next_sequence()

        self.write({'state': 'posted'})
        lines_of_moves_to_post = self.line_ids.filtered(lambda line: line.move_id.state != 'posted')
        if lines_of_moves_to_post:
            lines_of_moves_to_post.move_id._post(soft=False)

    def button_validate(self):
        if any(statement.state != 'posted' or not statement.all_lines_reconciled for statement in self):
            raise UserError(_('All the account entries lines must be processed in order to validate the statement.'))

        for statement in self:

            # Chatter.
            statement.message_post(body=_('Statement %s confirmed.', statement.name))

            # Bank statement report.
            if statement.journal_id.type == 'bank':
                content, content_type = self.env.ref('account.action_report_account_statement')._render(statement.id)
                self.env['ir.attachment'].create({
                    'name': statement.name and _("Bank Statement %s.pdf", statement.name) or _("Bank Statement.pdf"),
                    'type': 'binary',
                    'raw': content,
                    'res_model': statement._name,
                    'res_id': statement.id
                })

        self._check_balance_end_real_same_as_computed()
        self.write({'state': 'confirm', 'date_done': fields.Datetime.now()})

    def button_validate_or_action(self):
        if self.journal_type == 'cash' and not self.currency_id.is_zero(self.difference):
            return self.env['ir.actions.act_window']._for_xml_id('account.action_view_account_bnk_stmt_check')

        return self.button_validate()

    def button_reopen(self):
        ''' Move the bank statements back to the 'open' state. '''
        if any(statement.state == 'draft' for statement in self):
            raise UserError(_("Only validated statements can be reset to new."))

        self.write({'state': 'open'})
        self.line_ids.move_id.button_draft()
        self.line_ids.button_undo_reconciliation()

    def button_reprocess(self):
        """Move the bank statements back to the 'posted' state."""
        if any(statement.state != 'confirm' for statement in self):
            raise UserError(_("Only Validated statements can be reset to new."))

        self.write({'state': 'posted', 'date_done': False})

    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': self.env.ref('account.view_move_line_tree_grouped_bank_cash').id,
            'type': 'ir.actions.act_window',
            'domain': [('move_id', 'in', self.line_ids.move_id.ids)],
            'context': {
                'journal_id': self.journal_id.id,
                'group_by': 'move_id',
                'expand': True
            }
        }

    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        where_string = "WHERE journal_id = %(journal_id)s AND name != '/'"
        param = {'journal_id': self.journal_id.id}

        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', '!=', False)]
            previous_name = self.search(domain + [('date', '<', self.date)], order='date desc', limit=1).name
            if not previous_name:
                previous_name = self.search(domain, order='date desc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(previous_name)
            if sequence_number_reset == 'year':
                where_string += " AND date_trunc('year', date) = date_trunc('year', %(date)s) "
                param['date'] = self.date
            elif sequence_number_reset == 'month':
                where_string += " AND date_trunc('month', date) = date_trunc('month', %(date)s) "
                param['date'] = self.date
        return where_string, param

    def _get_starting_sequence(self):
        self.ensure_one()
        return "%s %s %04d/%02d/00000" % (self.journal_id.code, _('Statement'), self.date.year, self.date.month)


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherits = {'account.move': 'move_id'}
    _description = "Bank Statement Line"
    _order = "statement_id desc, date, sequence, id desc"
    _check_company_auto = True

    # FIXME: Fields having the same name in both tables are confusing (partner_id & state). We don't change it because:
    # - It's a mess to track/fix.
    # - Some fields here could be simplified when the onchanges will be gone in account.move.
    # Should be improved in the future.

    # == Business fields ==
    move_id = fields.Many2one(
        comodel_name='account.move',
        auto_join=True,
        string='Journal Entry', required=True, readonly=True, ondelete='cascade',
        check_company=True)
    statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
        string='Statement', index=True, required=True, ondelete='cascade',
        check_company=True)

    sequence = fields.Integer(help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    account_number = fields.Char(string='Bank Account Number', help="Technical field used to store the bank account number before its creation, upon the line's processing")
    partner_name = fields.Char(
        help="This field is used to record the third party name when importing bank statement in electronic format, "
             "when the partner doesn't exist yet in the database (or cannot be found).")
    transaction_type = fields.Char(string='Transaction Type')
    payment_ref = fields.Char(string='Label', required=True)
    amount = fields.Monetary(currency_field='currency_id')
    amount_currency = fields.Monetary(
        string="Amount in Currency",
        currency_field='foreign_currency_id',
        help="The amount expressed in an optional other currency if it is a multi-currency entry.",
    )
    foreign_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Foreign Currency",
        help="The optional other currency if it is a multi-currency entry.",
    )
    amount_residual = fields.Float(string="Residual Amount",
        compute="_compute_is_reconciled",
        store=True,
        help="The amount left to be reconciled on this statement line (signed according to its move lines' balance), expressed in its currency. This is a technical field use to speedup the application of reconciliation models.")
    currency_id = fields.Many2one('res.currency', string='Journal Currency')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner', ondelete='restrict',
        domain="['|', ('parent_id','=', False), ('is_company','=',True)]",
        check_company=True)
    payment_ids = fields.Many2many(
        comodel_name='account.payment',
        relation='account_payment_account_bank_statement_line_rel',
        string='Auto-generated Payments',
        help="Payments generated during the reconciliation of this bank statement lines.")

    # == Display purpose fields ==
    is_reconciled = fields.Boolean(string='Is Reconciled', store=True,
        compute='_compute_is_reconciled',
        help="Technical field indicating if the statement line is already reconciled.")
    state = fields.Selection(related='statement_id.state', string='Status', readonly=True)
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the liquidity account.
        - The lines using the transfer account.
        - The lines being not in one of the two previous categories.
        :return: (liquidity_lines, suspense_lines, other_lines)
        '''
        liquidity_lines = self.env['account.move.line']
        suspense_lines = self.env['account.move.line']
        other_lines = self.env['account.move.line']

        for line in self.move_id.line_ids:
            if line.account_id == self.journal_id.default_account_id:
                liquidity_lines += line
            elif line.account_id == self.journal_id.suspense_account_id:
                suspense_lines += line
            else:
                other_lines += line
        return liquidity_lines, suspense_lines, other_lines

    def _prepare_counterpart_amounts_using_st_line_rate(self, currency, balance, amount_currency):
        """ Convert the amounts passed as parameters to the statement line currency using the rates provided by the
        bank. The computed amounts are the one that could be set on the statement line as a counterpart journal item
        to fully paid the provided amounts as parameters.

        :param currency:        The currency in which is expressed 'amount_currency'.
        :param balance:         The amount expressed in company currency. Only needed when the currency passed as
                                parameter is neither the statement line's foreign currency, neither the journal's
                                currency.
        :param amount_currency: The amount expressed in the 'currency' passed as parameter.
        :return:                A python dictionary containing:
            * balance:          The amount to consider expressed in company's currency.
            * amount_currency:  The amount to consider expressed in statement line's foreign currency.
        """
        self.ensure_one()

        journal = self.journal_id
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id or company_currency
        foreign_currency = self.foreign_currency_id or journal_currency or company_currency

        journal_amount = self.amount
        if foreign_currency == journal_currency:
            transaction_amount = journal_amount
        else:
            transaction_amount = self.amount_currency
        if journal_currency == company_currency:
            company_amount = journal_amount
        elif foreign_currency == company_currency:
            company_amount = transaction_amount
        else:
            company_amount = journal_currency._convert(journal_amount, company_currency, journal.company_id, self.date)

        rate_journal2foreign_curr = journal_amount and abs(transaction_amount) / abs(journal_amount)
        rate_comp2journal_curr = company_amount and abs(journal_amount) / abs(company_amount)

        if currency == foreign_currency:
            trans_amount_currency = amount_currency
            if rate_journal2foreign_curr:
                journ_amount_currency = journal_currency.round(trans_amount_currency / rate_journal2foreign_curr)
            else:
                journ_amount_currency = 0.0
            if rate_comp2journal_curr:
                new_balance = company_currency.round(journ_amount_currency / rate_comp2journal_curr)
            else:
                new_balance = 0.0
        elif currency == journal_currency:
            trans_amount_currency = foreign_currency.round(amount_currency * rate_journal2foreign_curr)
            if rate_comp2journal_curr:
                new_balance = company_currency.round(amount_currency / rate_comp2journal_curr)
            else:
                new_balance = 0.0
        else:
            journ_amount_currency = journal_currency.round(balance * rate_comp2journal_curr)
            trans_amount_currency = foreign_currency.round(journ_amount_currency * rate_journal2foreign_curr)
            new_balance = balance

        return {
            'amount_currency': trans_amount_currency,
            'balance': new_balance,
        }

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current account.bank.statement.line
        record.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()

        if not counterpart_account_id:
            counterpart_account_id = self.journal_id.suspense_account_id.id

        if not counterpart_account_id:
            raise UserError(_(
                "You can't create a new statement line without a suspense account set on the %s journal.",
                self.journal_id.display_name,
            ))

        journal = self.journal_id
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id or company_currency
        foreign_currency = self.foreign_currency_id or journal_currency or company_currency

        journal_amount = self.amount
        if foreign_currency == journal_currency:
            transaction_amount = journal_amount
        else:
            transaction_amount = self.amount_currency
        if journal_currency == company_currency:
            company_amount = journal_amount
        elif foreign_currency == company_currency:
            company_amount = transaction_amount
        else:
            company_amount = journal_currency._convert(journal_amount, company_currency, journal.company_id, self.date)

        liquidity_line_vals = {
            'name': self.payment_ref,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'account_id': journal.default_account_id.id,
            'currency_id': journal_currency.id,
            'amount_currency': journal_amount,
            'debit': company_amount > 0 and company_amount or 0.0,
            'credit': company_amount < 0 and -company_amount or 0.0,
        }

        # Create the counterpart line values.
        counterpart_line_vals = {
            'name': self.payment_ref,
            'account_id': counterpart_account_id,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': foreign_currency.id,
            'amount_currency': -transaction_amount,
            'debit': -company_amount if company_amount < 0.0 else 0.0,
            'credit': company_amount if company_amount > 0.0 else 0.0,
        }
        return [liquidity_line_vals, counterpart_line_vals]

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('journal_id', 'currency_id', 'amount', 'foreign_currency_id', 'amount_currency',
                 'move_id.to_check',
                 'move_id.line_ids.account_id', 'move_id.line_ids.amount_currency',
                 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.currency_id',
                 'move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_is_reconciled(self):
        ''' Compute the field indicating if the statement lines are already reconciled with something.
        This field is used for display purpose (e.g. display the 'cancel' button on the statement lines).
        Also computes the residual amount of the statement line.
        '''
        for st_line in self:
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()

            # Compute residual amount
            if st_line.to_check:
                st_line.amount_residual = -st_line.amount_currency if st_line.foreign_currency_id else -st_line.amount
            elif suspense_lines.account_id.reconcile:
                st_line.amount_residual = sum(suspense_lines.mapped('amount_residual_currency'))
            else:
                st_line.amount_residual = sum(suspense_lines.mapped('amount_currency'))

            # Compute is_reconciled
            if not st_line.id:
                # New record: The journal items are not yet there.
                st_line.is_reconciled = False
            elif suspense_lines:
                # In case of the statement line comes from an older version, it could have a residual amount of zero.
                st_line.is_reconciled = suspense_lines.currency_id.is_zero(st_line.amount_residual)
            elif st_line.currency_id.is_zero(st_line.amount):
                st_line.is_reconciled = True
            else:
                # The journal entry seems reconciled.
                st_line.is_reconciled = True

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('amount', 'amount_currency', 'currency_id', 'foreign_currency_id', 'journal_id')
    def _check_amounts_currencies(self):
        ''' Ensure the consistency the specified amounts and the currencies. '''

        for st_line in self:
            if st_line.journal_id != st_line.statement_id.journal_id:
                raise ValidationError(_('The journal of a statement line must always be the same as the bank statement one.'))
            if st_line.foreign_currency_id == st_line.currency_id:
                raise ValidationError(_("The foreign currency must be different than the journal one: %s", st_line.currency_id.name))
            if not st_line.foreign_currency_id and st_line.amount_currency:
                raise ValidationError(_("You can't provide an amount in foreign currency without specifying a foreign currency."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        counterpart_account_ids = []

        for vals in vals_list:
            statement = self.env['account.bank.statement'].browse(vals['statement_id'])
            if statement.state != 'open' and self._context.get('check_move_validity', True):
                raise UserError(_("You can only create statement line in open bank statements."))

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'

            journal = statement.journal_id
            # Ensure the journal is the same as the statement one.
            vals['journal_id'] = journal.id
            vals['currency_id'] = (journal.currency_id or journal.company_id.currency_id).id
            if 'date' not in vals:
                vals['date'] = statement.date

            # Hack to force different account instead of the suspense account.
            counterpart_account_ids.append(vals.pop('counterpart_account_id', None))

        st_lines = super().create(vals_list)

        for i, st_line in enumerate(st_lines):
            counterpart_account_id = counterpart_account_ids[i]

            to_write = {'statement_line_id': st_line.id, 'narration': st_line.narration}
            if 'line_ids' not in vals_list[i]:
                to_write['line_ids'] = [(0, 0, line_vals) for line_vals in st_line._prepare_move_line_default_vals(counterpart_account_id=counterpart_account_id)]

            st_line.move_id.write(to_write)

            # Otherwise field narration will be recomputed silently (at next flush) when writing on partner_id
            self.env.remove_to_compute(st_line.move_id._fields['narration'], st_line.move_id)
        return st_lines

    def write(self, vals):
        # OVERRIDE
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    def unlink(self):
        # OVERRIDE to unlink the inherited account.move (move_id field) as well.
        moves = self.with_context(force_delete=True).mapped('move_id')
        res = super().unlink()
        moves.unlink()
        return res

    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.bank.statement.line <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.bank.statement.line regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            move = st_line.move_id
            move_vals_to_write = {}
            st_line_vals_to_write = {}

            if 'state' in changed_fields:
                if (st_line.state == 'open' and move.state != 'draft') or (st_line.state in ('posted', 'confirm') and move.state != 'posted'):
                    raise UserError(_(
                        "You can't manually change the state of journal entry %s, as it has been created by bank "
                        "statement %s."
                    ) % (st_line.move_id.display_name, st_line.statement_id.display_name))

            if 'line_ids' in changed_fields:
                liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
                company_currency = st_line.journal_id.company_id.currency_id
                journal_currency = st_line.journal_id.currency_id if st_line.journal_id.currency_id != company_currency else False

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state regarding its related statement line.\n"
                        "To be consistent, the journal entry must always have exactly one journal item involving the "
                        "bank/cash account."
                    ) % st_line.move_id.display_name)

                st_line_vals_to_write.update({
                    'payment_ref': liquidity_lines.name,
                    'partner_id': liquidity_lines.partner_id.id,
                })

                # Update 'amount' according to the liquidity line.

                if journal_currency:
                    st_line_vals_to_write.update({
                        'amount': liquidity_lines.amount_currency,
                    })
                else:
                    st_line_vals_to_write.update({
                        'amount': liquidity_lines.balance,
                    })

                if len(suspense_lines) == 1:

                    if journal_currency and suspense_lines.currency_id == journal_currency:

                        # The suspense line is expressed in the journal's currency meaning the foreign currency
                        # set on the statement line is no longer needed.

                        st_line_vals_to_write.update({
                            'amount_currency': 0.0,
                            'foreign_currency_id': False,
                        })

                    elif not journal_currency and suspense_lines.currency_id == company_currency:

                        # Don't set a specific foreign currency on the statement line.

                        st_line_vals_to_write.update({
                            'amount_currency': 0.0,
                            'foreign_currency_id': False,
                        })

                    else:

                        # Update the statement line regarding the foreign currency of the suspense line.

                        st_line_vals_to_write.update({
                            'amount_currency': -suspense_lines.amount_currency,
                            'foreign_currency_id': suspense_lines.currency_id.id,
                        })

                move_vals_to_write.update({
                    'partner_id': liquidity_lines.partner_id.id,
                    'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                })

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            st_line.write(move._cleanup_write_orm_values(st_line, st_line_vals_to_write))

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.bank.statement.line.
        :param changed_fields: A list containing all modified fields on account.bank.statement.line.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id', 'partner_id',
        )):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            company_currency = st_line.journal_id.company_id.currency_id
            journal_currency = st_line.journal_id.currency_id if st_line.journal_id.currency_id != company_currency else False

            line_vals_list = self._prepare_move_line_default_vals()
            line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]

            if suspense_lines:
                line_ids_commands.append((1, suspense_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in other_lines:
                line_ids_commands.append((2, line.id))

            st_line_vals = {
                'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                'line_ids': line_ids_commands,
            }
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals['partner_id'] = st_line.partner_id.id
            st_line.move_id.write(st_line_vals)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _get_st_line_strings_for_matching(self, allowed_fields=None):
        """ Collect the strings that could be used on the statement line to perform some matching.

        :param allowed_fields: A explicit list of fields to consider.
        :return: A list of strings.
        """
        self.ensure_one()

        def _get_text_value(field_name):
            if self._fields[field_name].type == 'html':
                return html2plaintext(self[field_name])
            else:
                return self[field_name]

        st_line_text_values = []
        if allowed_fields is None or 'payment_ref' in allowed_fields:
            value = _get_text_value('payment_ref')
            if value:
                st_line_text_values.append(value)
        if allowed_fields is None or 'narration' in allowed_fields:
            value = _get_text_value('narration')
            if value:
                st_line_text_values.append(value)
        if allowed_fields is None or 'ref' in allowed_fields:
            value = _get_text_value('ref')
            if value:
                st_line_text_values.append(value)
        return st_line_text_values

    def _get_default_amls_matching_domain(self):
        return [
            # Base domain.
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            # Reconciliation domain.
            ('reconciled', '=', False),
            ('account_id.reconcile', '=', True),
            # Special domain for payments.
            '|',
            ('account_id.account_type', 'not in', ('asset_receivable', 'liability_payable')),
            ('payment_id', '=', False),
            # Special domain for statement lines.
            ('statement_line_id', '!=', self.id),
        ]

    def _retrieve_partner(self):
        self.ensure_one()

        # Retrieve the partner from the statement line.
        if self.partner_id:
            return self.partner_id

        # Retrieve the partner from the bank account.
        if self.account_number:
            account_number_nums = sanitize_account_number(self.account_number)
            if account_number_nums:
                domain = [('sanitized_acc_number', 'ilike', account_number_nums)]
                for extra_domain in ([('company_id', '=', self.company_id.id)], []):
                    bank_accounts = self.env['res.partner.bank'].search(extra_domain + domain)
                    if len(bank_accounts.partner_id) == 1:
                        return bank_accounts.partner_id

        # Retrieve the partner from the partner name.
        if self.partner_name:
            domain = [
                ('parent_id', '=', False),
                ('name', 'ilike', self.partner_name),
            ]
            for extra_domain in ([('company_id', '=', self.company_id.id)], []):
                partner = self.env['res.partner'].search(extra_domain + domain, limit=1)
                if partner:
                    return partner

        # Retrieve the partner from the reconcile models.
        rec_models = self.env['account.reconcile.model'].search([
            ('rule_type', '!=', 'writeoff_button'),
            ('company_id', '=', self.company_id.id),
        ])
        for rec_model in rec_models:
            partner = rec_model._get_partner_from_mapping(self)
            if partner and rec_model._is_applicable_for(self, partner):
                return partner

        # Retrieve the partner from statement line text values.
        st_line_text_values = self._get_st_line_strings_for_matching()
        unaccent = get_unaccent_wrapper(self._cr)
        sub_queries = []
        params = []
        for text_value in st_line_text_values:
            if not text_value:
                continue

            # Find a partner having a name contained inside the statement line values.
            # Take care a partner could contain some special characters in its name that needs to be escaped.
            sub_queries.append(rf'''
                {unaccent("%s")} ~* ('^' || (
                   SELECT STRING_AGG(CONCAT('(?=.*\m', chunk[1], '\M)'), '')
                   FROM regexp_matches({unaccent('name')}, '\w{{3,}}', 'g') AS chunk
                ))
            ''')
            params.append(text_value)

        if sub_queries:
            self.env['res.partner'].flush_model(['company_id', 'name'])
            self._cr.execute(
                '''
                    SELECT id
                    FROM res_partner
                    WHERE (company_id IS NULL OR company_id = %s)
                        AND name IS NOT NULL
                        AND (''' + ') OR ('.join(sub_queries) + ''')
                ''',
                [self.company_id.id] + params,
            )
            rows = self._cr.fetchall()
            if len(rows) == 1:
                return self.env['res.partner'].browse(rows[0][0])

        return self.env['res.partner']

    def _find_or_create_bank_account(self):
        bank_account = self.env['res.partner.bank'].search([
            ('acc_number', '=', self.account_number),
            ('partner_id', '=', self.partner_id.id),
        ])
        if not bank_account:
            bank_account = self.env['res.partner.bank'].create({
                'acc_number': self.account_number,
                'partner_id': self.partner_id.id,
            })
        return bank_account

    def button_undo_reconciliation(self):
        ''' Undo the reconciliation mades on the statement line and reset their journal items
        to their original states.
        '''
        self.line_ids.remove_move_reconcile()
        self.payment_ids.unlink()

        for st_line in self:
            st_line.with_context(force_delete=True).write({
                'to_check': False,
                'line_ids': [(5, 0)] + [(0, 0, line_vals) for line_vals in st_line._prepare_move_line_default_vals()],
            })
