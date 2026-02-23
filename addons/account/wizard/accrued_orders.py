# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import json
from odoo import models, fields, api, _, Command
from odoo.tools import float_is_zero, format_date
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import formatLang


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
        required=True,
        string='Accrual Account',
        check_company=True,
        domain="[('account_type', '=', 'liability_current')] if context.get('active_model') in ['purchase.order', 'purchase.order.line'] else [('account_type', '=', 'asset_current')]",
    )
    preview_data = fields.Text(compute='_compute_preview_data')
    display_amount = fields.Boolean(compute='_compute_display_amount')

    @api.depends('date', 'amount')
    def _compute_display_amount(self):
        single_order = len(self.env.context['active_ids']) == 1
        for record in self:
            preview_data = json.loads(self.preview_data)
            lines = preview_data.get('groups_vals', [])[0].get('items_vals', [])
            record.display_amount = record.amount or (single_order and not lines)

    @api.depends('date')
    def _compute_reversal_date(self):
        for record in self:
            if not record.reversal_date or record.reversal_date <= record.date:
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

    @api.depends('date', 'journal_id', 'account_id', 'amount')
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

    def _get_computed_account(self, order, product, is_purchase):
        accounts = product.with_company(order.company_id).product_tmpl_id.get_product_accounts(fiscal_pos=order.fiscal_position_id)
        if is_purchase:
            return accounts['expense']
        else:
            return accounts['income']

    def _compute_move_vals(self):
        def _get_aml_vals(order, balance, amount_currency, account_id, label="", analytic_distribution=None):
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

        def _ellipsis(string, size):
            if len(string) > size:
                return string[0:size - 3] + '...'
            return string

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
        if orders.currency_id and len(orders.currency_id) > 1:
            raise UserError(_('Cannot create an accrual entry with orders in different currencies.'))
        orders_with_entries = []
        total_balance = 0.0
        amounts_by_perpetual_account = defaultdict(float)
        price_diff_values = []

        for order, product_lines in lines.grouped('order_id').items():
            if len(orders) == 1 and product_lines and self.amount and order.order_line:
                total_balance = self.amount
                order_line = product_lines[0]
                account = self._get_computed_account(order, order_line.product_id, is_purchase)
                distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
                values = _get_aml_vals(order, self.amount, 0, account.id, label=_('Manual entry'), analytic_distribution=distribution)
                move_lines.append(Command.create(values))
            else:
                accrual_entry_date = self.env.context.get('accrual_entry_date', self.date)
                order_lines = lines.with_context(accrual_entry_date=accrual_entry_date).filtered(
                    # We only want non-comment lines (no sections, notes, ...) and include all lines
                    # for purchase orders but exclude downpayment lines for sales orders.
                    lambda l: not l.display_type and not l.is_downpayment and
                    l.id in order.order_line.ids and
                    fields.Float.compare(
                        l.amount_to_invoice_at_date,
                        0,
                        precision_rounding=l.product_uom_id.rounding,
                    ) != 0
                )
                for order_line in order_lines:
                    product = order_line.product_id
                    if is_purchase:
                        # Compute the price unit from the amount to invoice if there is one,
                        # otherwise use the PO line price unit.
                        price_unit = order_line.price_unit
                        quantity_to_invoice = order_line.qty_invoiced_at_date - order_line.qty_received_at_date
                        if quantity_to_invoice >= 1:
                            posted_invoice_lines = order_line.invoice_lines.filtered(lambda ivl:
                                ivl.move_id.state == 'posted' and ivl.date <= accrual_entry_date
                            )
                            invoiced_values = sum(ivl.price_subtotal for ivl in posted_invoice_lines)
                            received_values = order_line.qty_received_at_date * order_line.price_unit
                            value_to_invoice = invoiced_values - received_values
                            price_unit = value_to_invoice / quantity_to_invoice

                        expense_account, stock_variation_account = self._get_product_expense_and_stock_var_accounts(product)
                        account = stock_variation_account if stock_variation_account else self._get_computed_account(order, order_line.product_id, is_purchase)
                        if any(tax.price_include for tax in order_line.tax_ids):
                            # As included taxes are not taken into account in the price_unit, we need to compute the price_subtotal
                            qty_to_invoice = order_line.qty_received_at_date - order_line.qty_invoiced_at_date
                            price_subtotal = order_line.tax_ids.compute_all(
                                price_unit,
                                currency=order_line.order_id.currency_id,
                                quantity=qty_to_invoice,
                                product=order_line.product_id,
                                partner=order_line.order_id.partner_id)['total_excluded']
                        else:
                            price_subtotal = (order_line.qty_received_at_date - order_line.qty_invoiced_at_date) * price_unit
                        amount_currency = order_line.currency_id.round(price_subtotal)
                        amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
                        label = _(
                            '%(order)s - %(order_line)s; %(quantity_billed)s Billed, %(quantity_received)s Received at %(unit_price)s each',
                            order=order.name,
                            order_line=_ellipsis(order_line.name, 20),
                            quantity_billed=order_line.qty_invoiced_at_date,
                            quantity_received=order_line.qty_received_at_date,
                            unit_price=formatLang(self.env, price_unit, currency_obj=order.currency_id),
                        )

                        # Generate price diff account move lines if needed.
                        price_diff_account = False
                        if product.cost_method == 'standard':
                            price_diff_account = product.categ_id.property_price_difference_account_id
                        if price_diff_account:
                            qty_to_invoice = order_line.qty_received_at_date - order_line.qty_invoiced_at_date
                            diff_label = _('%(order)s - %(order_line)s; price difference for %(product)s',
                                order=order.name,
                                order_line=_ellipsis(order_line.name, 20),
                                product=product.display_name
                            )
                            unit_price_diff = order_line.product_id.standard_price - price_unit
                            price_diff = qty_to_invoice * unit_price_diff
                            if not float_is_zero(price_diff, precision_rounding=order_line.currency_id.rounding):
                                price_diff_values.append(_get_aml_vals(
                                    order,
                                    -price_diff,
                                    price_diff,
                                    price_diff_account.id,
                                    label=diff_label,
                                    analytic_distribution=False
                                ))
                                price_diff_values.append(_get_aml_vals(
                                    order,
                                    price_diff,
                                    price_diff,
                                    product.categ_id.account_stock_variation_id.id,
                                    label=diff_label,
                                    analytic_distribution=False
                                ))
                    else:
                        qty_to_invoice = order_line.qty_delivered_at_date - order_line.qty_invoiced_at_date
                        expense_account, stock_variation_account = self._get_product_expense_and_stock_var_accounts(product)
                        account = self._get_computed_account(order, product, is_purchase)
                        price_unit = order_line.price_unit
                        if qty_to_invoice > 0:
                            # Invoices to be issued.
                            amount_currency = order_line.amount_to_invoice_at_date
                            amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
                        elif qty_to_invoice < 0:
                            # Invoiced not delivered.
                            posted_invoice_line = order_line.invoice_lines.filtered(lambda ivl: ivl.move_id.state == 'posted')[0]
                            price_unit = posted_invoice_line.price_unit
                            amount_currency = qty_to_invoice * price_unit
                            amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
                        label = _(
                            '%(order)s - %(order_line)s; %(quantity_invoiced)s Invoiced, %(quantity_delivered)s Delivered at %(unit_price)s each',
                            order=order.name,
                            order_line=_ellipsis(order_line.name, 20),
                            quantity_invoiced=order_line.qty_invoiced_at_date,
                            quantity_delivered=order_line.qty_delivered_at_date,
                            unit_price=formatLang(self.env, price_unit, currency_obj=order.currency_id),
                        )
                        if expense_account and stock_variation_account:
                            # Evaluate if there are more invoiced or more delivered.
                            if qty_to_invoice > 0:
                                # Invoices to be issued.
                                # First, compute the delivered value.
                                stock_moves = order_line.move_ids.filtered(lambda m: m.state == 'done')
                                delivered_value = sum(m.value for m in stock_moves)
                                # Then, compute the already invoiced value.
                                posted_invoice_lines = order_line.invoice_lines.filtered(lambda ivl: ivl.move_id.state == 'posted')
                                expense_invoice_lines = posted_invoice_lines.move_id.line_ids.filtered(lambda ivl:
                                    ivl.move_id.state == 'posted' and
                                    ivl.account_id == expense_account
                                )
                                invoiced_value = sum(l.balance for l in expense_invoice_lines)
                                # The amount to invoice is equal to the delivered value minus the already invoiced value.
                                perpetual_amount = delivered_value - invoiced_value
                                amounts_by_perpetual_account[expense_account, stock_variation_account] += perpetual_amount
                            elif qty_to_invoice < 0:
                                # Invoiced not delivered.
                                label += " (*)"
                                posted_invoice_lines = order_line.invoice_lines.filtered(lambda ivl: ivl.move_id.state == 'posted')
                                expense_invoice_lines = posted_invoice_lines.move_id.line_ids.filtered(lambda ivl:
                                    ivl.move_id.state == 'posted' and
                                    ivl.account_id == expense_account
                                )
                                invoiced_quantity = sum(posted_invoice_lines.mapped('quantity'))
                                sum_amount = sum(expense_invoice_lines.mapped('debit'))
                                invoiced_unit_price = sum_amount / invoiced_quantity
                                perpetual_amount = invoiced_unit_price * qty_to_invoice
                                amounts_by_perpetual_account[expense_account, stock_variation_account] += perpetual_amount

                    distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
                    values = _get_aml_vals(order, amount, amount_currency, account.id, label=label, analytic_distribution=distribution)
                    move_lines.append(Command.create(values))
                    total_balance += amount

        if not self.company_id.currency_id.is_zero(total_balance):
            # globalized counterpart for the whole orders selection
            analytic_distribution = {}
            total = sum(order.amount_total for order in orders)
            for line in orders.order_line:
                ratio = line.price_total / total
                if not line.analytic_distribution:
                    continue
                for account_id, distribution in line.analytic_distribution.items():
                    analytic_distribution.update({account_id : analytic_distribution.get(account_id, 0) + distribution*ratio})
            values = _get_aml_vals(orders, -total_balance, 0.0, self.account_id.id, label=_('Accrued total'), analytic_distribution=analytic_distribution)
            move_lines.append(Command.create(values))

        for (expense_account, stock_variation_account), amount in amounts_by_perpetual_account.items():
            if amount == 0:
                continue
            if amount > 0:
                label = _('(*) Goods Delivered not Invoiced (perpetual valuation)')
            else:
                label = _('(*) Goods Invoiced not Delivered (perpetual valuation)')
            values = _get_aml_vals(orders, amount, 0.0, stock_variation_account.id, label=label)
            move_lines.append(Command.create(values))
            values = _get_aml_vals(orders, -amount, 0.0, expense_account.id, label=label)
            move_lines.append(Command.create(values))

        for values in price_diff_values:
            move_lines.append(Command.create(values))

        move_type = _('Expense') if is_purchase else _('Revenue')
        move_vals = {
            'ref': _('Accrued %(entry_type)s entry as of %(date)s', entry_type=move_type, date=format_date(self.env, self.date)),
            'name': '/',
            'journal_id': self.journal_id.id,
            'date': self.date,
            'line_ids': move_lines,
            'currency_id': orders.currency_id.id or self.company_id.currency_id.id,
        }
        return move_vals, orders_with_entries

    def _get_accrual_message_body(self, move, reverse_move):
        self.ensure_one()
        return _(
            'Accrual entry created on %(date)s: %(accrual_entry)s.\
                And its reverse entry: %(reverse_entry)s.',
            date=self.date,
            accrual_entry=move._get_html_link(),
            reverse_entry=reverse_move._get_html_link(),
        )

    def create_entries(self):
        self.ensure_one()

        if self.reversal_date <= self.date:
            raise UserError(_('Reversal date must be posterior to date.'))
        move_vals, orders_with_entries = self._compute_move_vals()
        move = self.env['account.move'].create(move_vals)
        move._post()
        reverse_move = move._reverse_moves(default_values_list=[{
            'ref': _('Reversal of: %s', move.ref),
            'name': '/',
            'date': self.reversal_date,
        }])
        reverse_move._post()
        for order in orders_with_entries:
            order.message_post(body=self._get_accrual_message_body(move, reverse_move))
        return {
            'name': _('Accrual Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', (move | reverse_move).ids)],
        }

    @api.model
    def _get_product_expense_and_stock_var_accounts(self, product):
        return (False, False)
