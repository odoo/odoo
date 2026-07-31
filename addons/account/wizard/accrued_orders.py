# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils, format_date


def ellipsis(string, size):
    if len(string) > size:
        return string[0:size - 3] + '...'
    return string


class AccountAccruedOrdersWizard(models.TransientModel):
    _name = 'account.accrued.orders.wizard'
    _description = 'Accrued Orders Wizard'
    _check_company_auto = True

    def _get_default_company(self):
        if not self.env.context.get('active_model'):
            return
        orders = self.env[self.env.context['active_model']].browse(self.env.context['active_ids'])
        return orders and orders[0].company_id.id

    def _get_default_date(self):
        return date_utils.get_month(fields.Date.context_today(self))[0] - relativedelta(days=1)

    accrual_type = fields.Selection(
        string="Accrual Type",
        selection=[
            ('bill_to_receive', "Bills to receive"),
            ('billed_not_received', "Billed not received"),
            ('invoice_to_be_issued', "Invoices to be issued"),
            ('invoiced_not_delivered', "Invoiced not delivered"),
        ],
        required=True,
    )
    company_id = fields.Many2one('res.company', default=_get_default_company)
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        domain="[('type', '=', 'general')]",
        required=True,
        check_company=True,
        string='Journal',
    )
    date = fields.Date(default=_get_default_date, required=True)
    reversal_date = fields.Date(
        compute="_compute_reversal_date",
        required=True,
        readonly=False,
        store=True,
        precompute=True,
    )
    amount = fields.Monetary(string='Amount', help="Specify an arbitrary value that will be accrued on a \
        default account for the entire order, regardless of the products on the different lines.")
    currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Accrual Account',
        check_company=True,
        domain="[('account_type', '=', 'liability_current')] if context.get('active_model') in ['purchase.order', 'purchase.order.line'] else [('account_type', '=', 'asset_current')]",
    )
    preview_data = fields.Text(compute='_compute_preview_data')
    display_amount = fields.Boolean(compute='_compute_display_amount')
    duplicate_entry_id = fields.Many2one(comodel_name='account.move', compute='_compute_duplicate_entry')
    duplicate_price_total = fields.Monetary(related='duplicate_entry_id.amount_total')

    @api.depends('date', 'amount', 'account_id')
    def _compute_display_amount(self):
        single_order = len(self.env.context['active_ids']) == 1
        for record in self:
            preview_data = json.loads(self.preview_data)
            lines = preview_data.get('groups_vals', [])[0].get('items_vals', [])
            record.display_amount = record.amount or (single_order and not lines)

    @api.depends('date')
    def _compute_reversal_date(self):
        for record in self:
            if record.date and (not record.reversal_date or record.reversal_date <= record.date):
                record.reversal_date = record.date + relativedelta(days=1)
            else:
                record.reversal_date = record.reversal_date

    @api.depends('company_id')
    def _compute_journal_id(self):
        for record in self:
            record.journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(record.company_id),
                ('type', '=', 'general')
            ], limit=1)

    @api.depends('date', 'journal_id', 'account_id', 'amount', 'accrual_type')
    def _compute_preview_data(self):
        for record in self:
            preview_vals = [self.env['account.move']._move_dict_to_preview_vals(
                record._compute_move_vals()[0],
                record.company_id.currency_id,
            )]
            preview_columns = [
                {'field': 'account_id', 'label': _('Account')},
                {'field': 'name', 'label': _('Label')},
                {'field': 'debit', 'label': _('Debit'), 'class': 'text-end text-nowrap'},
                {'field': 'credit', 'label': _('Credit'), 'class': 'text-end text-nowrap'},
            ]
            record.preview_data = json.dumps({
                'groups_vals': preview_vals,
                'options': {
                    'columns': preview_columns,
                },
            })

    @api.depends('date', 'journal_id', 'preview_data')
    def _compute_duplicate_entry(self):
        for record in self:
            if not record.preview_data:
                record.duplicate_entry_id = False
                continue

            data = json.loads(record.preview_data)
            ref = data['groups_vals'][0]['group_name'].split(', ')[1]
            record.duplicate_entry_id = self.env['account.move'].search([
                ('date', '=', record.date),
                ('journal_id', '=', record.journal_id.id),
                ('ref', '=', ref),
                ('state', 'in', ('draft', 'posted')),
            ], order='id desc', limit=1)

    def _get_computed_account(self, order, product, is_purchase):
        accounts = product.with_company(order.company_id).product_tmpl_id.get_product_accounts(fiscal_pos=order.fiscal_position_id)
        if is_purchase:
            return accounts['expense']
        else:
            return accounts['income']

    def _get_aml_vals(self, is_purchase, order, balance, amount_currency, account_id, label="", analytic_distribution=None):
        # `balance`/`amount_currency` use the expense/income account's sign
        # convention (debit positive); flip for sale, whose entries mirror
        # the purchase ones.
        if not is_purchase:
            balance *= -1
            amount_currency *= -1
        values = {
            'name': label,
            'debit': balance if balance > 0 else 0.0,
            'credit': balance * -1 if balance < 0 else 0.0,
            'account_id': account_id,
        }
        if analytic_distribution:
            values.update({
                'analytic_distribution': analytic_distribution,
            })
        if len(order) == 1 and self.company_id.currency_id != order.currency_id:
            values.update({
                'amount_currency': amount_currency,
                'currency_id': order.currency_id.id,
            })
        return values

    def _merge_aml_vals(self, vals_list):
        """ Merge account.move.line vals (as built by `_get_aml_vals`) that share the same
        account and currency into one line each, summing their balance and blending their
        analytic distributions (weighted by each line's own balance). A merged line's
        `amount_currency` is zeroed out, like the wizard's other consolidated lines: a
        combined foreign-currency total across heterogeneous source lines isn't a
        meaningful figure. Lines posted to a distinct account, or the only line on their
        account, are left untouched.
        """
        groups = {}
        for vals in vals_list:
            groups.setdefault((vals['account_id'], vals.get('currency_id')), []).append(vals)

        merged_list = []
        for group in groups.values():
            if len(group) == 1:
                merged_list.append(group[0])
                continue

            balances = [vals['debit'] - vals['credit'] for vals in group]
            total_balance = sum(balances)
            total_weight = sum(abs(balance) for balance in balances)
            analytic_distribution = {}
            for vals, balance in zip(group, balances):
                weight = abs(balance) / total_weight if total_weight else 0.0
                for account_id, percentage in (vals.get('analytic_distribution') or {}).items():
                    analytic_distribution[account_id] = analytic_distribution.get(account_id, 0.0) + percentage * weight

            merged_vals = dict(group[0])
            merged_vals['debit'] = total_balance if total_balance > 0 else 0.0
            merged_vals['credit'] = -total_balance if total_balance < 0 else 0.0
            if 'amount_currency' in merged_vals:
                merged_vals['amount_currency'] = 0.0
            if analytic_distribution:
                merged_vals['analytic_distribution'] = analytic_distribution
            else:
                merged_vals.pop('analytic_distribution', None)
            merged_list.append(merged_vals)
        return merged_list

    def _get_accrual_lines(self, order, lines, accrual_entry_date):
        """ Of `lines` (candidates from a single order), the ones that still
        need an accrual as of `accrual_entry_date`. The amount check can't be
        a domain since it depends on the `accrual_entry_date` context.
        """
        candidate_lines = (lines & order.order_line).filtered_domain(lines._get_accrual_domain())
        dated_lines = candidate_lines.with_context(accrual_entry_date=accrual_entry_date)
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit')
        return dated_lines.filtered(
            lambda l: fields.Float.compare(l.amount_to_invoice_at_date, 0, precision_digits=precision_digits) != 0
        )

    def _compute_move_vals(self):
        self.ensure_one()
        move_lines = []
        active_model = self.env.context.get('active_model')
        if active_model in ['purchase.order.line', 'sale.order.line']:
            lines = self.env[active_model].with_company(self.company_id).browse(self.env.context['active_ids'])
            orders = lines.order_id
        else:
            orders = self.env[active_model].with_company(self.company_id).browse(self.env.context['active_ids'])
            lines = orders.order_line.filtered(lambda x: x.product_id)
        is_purchase = orders._name == 'purchase.order'

        if orders.filtered(lambda o: o.company_id != self.company_id):
            raise UserError(_('Entries can only be created for a single company at a time.'))
        mixed_currencies = len(orders.currency_id) > 1
        if mixed_currencies and not self.env.context.get('accrual_allow_mixed_currencies'):
            raise UserError(_('Cannot create an accrual entry with orders in different currencies.'))
        orders_with_entries = []
        order_lines_with_entries = lines.browse()
        total_balance = 0.0

        for order, product_lines in lines.grouped('order_id').items():
            if len(orders) == 1 and product_lines and self.amount and order.order_line:
                total_balance = self.amount
                order_line = product_lines[0]
                account = self._get_computed_account(order, order_line.product_id, is_purchase)
                distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
                values = self._get_aml_vals(is_purchase, order, self.amount, 0, account.id, label=_('Manual entry'), analytic_distribution=distribution)
                move_lines.append(Command.create(values))
            else:
                accrual_entry_date = self.env.context.get('accrual_entry_date')
                accrual_entry_date = fields.Date.from_string(accrual_entry_date) if accrual_entry_date else self.date
                order_lines = self._get_accrual_lines(order, lines, accrual_entry_date)
                order_lines_with_entries |= order_lines
                main_vals_list, main_counterpart_vals_list = self._get_accrual_main_line_vals(order_lines, is_purchase, accrual_entry_date)
                inventory_vals_list, counterpart_vals_list = self._get_accrual_cogs_line_vals(order_lines, is_purchase, accrual_entry_date)
                for vals in main_vals_list + main_counterpart_vals_list + inventory_vals_list + counterpart_vals_list:
                    move_lines.append(Command.create(vals))

        # Manual amount case: a single globalized counterpart on the manually chosen account.
        if not self.company_id.currency_id.is_zero(total_balance):
            analytic_distribution = {}
            total = sum(order.amount_total for order in orders)
            for line in orders.order_line:
                ratio = line.price_total / total if total else 0.0
                if not line.analytic_distribution:
                    continue
                for account_id, distribution in line.analytic_distribution.items():
                    analytic_distribution.update({account_id : analytic_distribution.get(account_id, 0) + distribution*ratio})
            values = self._get_aml_vals(is_purchase, orders, -total_balance, 0.0, self.account_id.id, label=_('Accrued total'), analytic_distribution=analytic_distribution)
            move_lines.append(Command.create(values))

        ref = None
        if accrual_type_string := dict(self._fields['accrual_type']._description_selection(self.env)).get(self.accrual_type):
            date = format_date(self.env, self.date)
            ref = _("%(accrual_type)s entry as of %(date)s", accrual_type=accrual_type_string, date=date)

        move_vals = {
            'ref': ref,
            'name': '/',
            'journal_id': self.journal_id.id,
            'date': self.date,
            'line_ids': move_lines,
            'currency_id': self.company_id.currency_id.id if mixed_currencies else (orders.currency_id.id or self.company_id.currency_id.id),
        }
        return move_vals, orders_with_entries, order_lines_with_entries

    def _get_accrual_message_body(self, move, reverse_move):
        self.ensure_one()
        return _(
            'Accrual entry created on %(date)s: %(accrual_entry)s.\
                And its reverse entry: %(reverse_entry)s.',
            date=self.date,
            accrual_entry=move._get_html_link(),
            reverse_entry=reverse_move._get_html_link(),
        )

    def create_entries(self, auto_post=True):
        self.ensure_one()

        if self.reversal_date <= self.date:
            raise UserError(_('Reversal date must be posterior to date.'))

        # Try to unlink the duplicate entry and its reversal
        if self.duplicate_entry_id:
            original_reverse_entry = self.env['account.move'].search([
                ('reversed_entry_id', '=', self.duplicate_entry_id.id),
            ])

            moves_to_delete = self.duplicate_entry_id | original_reverse_entry
            moves_to_delete._unlink_or_reverse(default_values_list=[
                {
                    'ref': _("Reversal of: %s", move.ref),
                    'date': self.date if move == self.duplicate_entry_id else self.reversal_date,
                }
                for move in moves_to_delete
            ])

        move_vals, orders_with_entries, order_lines_with_entries = self._compute_move_vals()
        move = self.env['account.move'].create(move_vals)
        order_lines_with_entries.accrual_move_ids = [Command.link(move.id)]
        reverse_move = move._reverse_moves(default_values_list=[{
            'ref': _('Reversal of: %s', move.ref),
            'name': '/',
            'date': self.reversal_date,
            # Posted on its own date by the daily auto-post cron, not right away: it must stay
            # draft until then, or its reversing effect (accounting and quantity alike) would
            # apply immediately and cancel the accrual out before it's ever seen.
            'auto_post': 'at_date',
        }])
        if auto_post:
            move._post()
        for order in orders_with_entries:
            order.message_post(body=self._get_accrual_message_body(move, reverse_move))
        return {
            'name': _('Accrual Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', (move | reverse_move).ids)],
        }

    def open_duplicate(self):
        self.ensure_one()
        if self.duplicate_entry_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Duplicate Entry',
                'res_model': 'account.move',
                'res_id': self.duplicate_entry_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def _get_accrual_main_line_vals(self, order_lines, is_purchase, accrual_entry_date):
        """ Hook overridden by purchase/sale: for each line in `order_lines`, its expense/
        revenue line and its accrual counterpart (and, for purchase's standard-cost
        products, its price-difference pair).

        :return: (main_vals_list, counterpart_vals_list), each a list of account.move.line
            vals (built via `_get_aml_vals`) ready for `Command.create` — respectively the
            expense/revenue side (plus the price-difference pair, for purchase's
            standard-cost products), and its accrual counterpart posted to the
            bills_to_receive/billed_not_received/invoices_to_issue/invoiced_not_delivered
            account.
        """
        raise NotImplementedError

    def _get_accrual_cogs_line_vals(self, order_lines, is_purchase, accrual_entry_date):
        """ Hook overridden by purchase/sale: the perpetual-valuation adjustment needed, for
        real-time-valued storable products among `order_lines`, because perpetual valuation
        already posts stock movements in real time instead of waiting for the bill/invoice.

        :return: (inventory_vals_list, counterpart_vals_list), each a list of account.move.line
            vals (built via `_get_aml_vals`) ready for `Command.create` — respectively the
            stock-valuation side of the adjustment, and its offsetting entry on the product's
            expense account.
        """
        return [], []
