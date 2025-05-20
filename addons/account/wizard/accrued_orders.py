# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
import json
from odoo import models, fields, api, _, Command
from odoo.tools import format_date
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import formatLang

class AccruedExpenseRevenue(models.TransientModel):
    _name = 'account.accrued.orders.wizard'
    _description = 'Accrued Orders Wizard'
    _check_company_auto = True

    def _get_default_company(self):
        if not self._context.get('active_model'):
            return
        orders = self.env[self._context['active_model']].browse(self._context['active_ids'])
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
        domain="[('account_type', '=', 'liability_current')] if context.get('active_model') == 'purchase.order' else [('account_type', '=', 'asset_current')]",
    )
    preview_data = fields.Text(compute='_compute_preview_data')
    display_amount = fields.Boolean(compute='_compute_display_amount')

    @api.depends('date', 'amount')
    def _compute_display_amount(self):
        single_order = len(self._context['active_ids']) == 1
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
        is_purchase = self.env.context.get('active_model') == 'purchase.order'
        orders = self.env[self._context['active_model']].with_company(self.company_id).browse(self._context['active_ids'])

        if orders.filtered(lambda o: o.company_id != self.company_id):
            raise UserError(_('Entries can only be created for a single company at a time.'))
        if orders.currency_id and len(orders.currency_id) > 1:
            raise UserError(_('Cannot create an accrual entry with orders in different currencies.'))
        orders_with_entries = []
        fnames = []
        total_balance = 0.0
        for order in orders:
            product_lines = order.order_line.filtered(lambda x: x.product_id)
            if len(orders) == 1 and product_lines and self.amount and order.order_line:
                total_balance = self.amount
                order_line = product_lines[0]
                account = self._get_computed_account(order, order_line.product_id, is_purchase)
                distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
                values = _get_aml_vals(order, self.amount, 0, account.id, label=_('Manual entry'), analytic_distribution=distribution)
                move_lines.append(Command.create(values))
            else:
                # create a virtual order that will allow to recompute the qty delivered/received (and dependancies)
                # without actually writing anything on the real record (field is computed and stored)
                o = order.new(origin=order)
                if is_purchase:
                    o.order_line.with_context(accrual_entry_date=self.date)._compute_qty_received()
                    o.order_line.with_context(accrual_entry_date=self.date)._compute_qty_invoiced()
                else:
                    o.order_line.with_context(accrual_entry_date=self.date)._compute_qty_delivered()
                    o.order_line.with_context(accrual_entry_date=self.date)._compute_qty_invoiced()
                    o.order_line.with_context(accrual_entry_date=self.date)._compute_untaxed_amount_invoiced()
                    o.order_line.with_context(accrual_entry_date=self.date)._compute_qty_to_invoice()
                lines = o.order_line.filtered(
                    # We only want lines that are not sections or notes and include all lines
                    # for purchase orders but exclude downpayment lines for sales orders.
                    lambda l: l.display_type not in ['line_section', 'line_note'] and not l.is_downpayment and
                    fields.Float.compare(
                        l.qty_to_invoice,
                        0,
                        precision_rounding=l.product_uom.rounding,
                    ) != 0
                )
                for order_line in lines:
                    if is_purchase:
                        account = self._get_computed_account(order, order_line.product_id, is_purchase)
                        if any(tax.price_include for tax in order_line.taxes_id):
                            # As included taxes are not taken into account in the price_unit, we need to compute the price_subtotal
                            price_subtotal = order_line.taxes_id.compute_all(
                                order_line.price_unit,
                                currency=order_line.order_id.currency_id,
                                quantity=order_line.qty_to_invoice,
                                product=order_line.product_id,
                                partner=order_line.order_id.partner_id)['total_excluded']
                        else:
                            price_subtotal = order_line.qty_to_invoice * order_line.price_unit
                        amount_currency = order_line.currency_id.round(price_subtotal)
                        amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
                        fnames = ['qty_to_invoice', 'qty_received', 'qty_invoiced', 'invoice_lines']
                        label = _(
                            '%(order)s - %(order_line)s; %(quantity_billed)s Billed, %(quantity_received)s Received at %(unit_price)s each',
                            order=order.name,
                            order_line=_ellipsis(order_line.name, 20),
                            quantity_billed=order_line.qty_invoiced,
                            quantity_received=order_line.qty_received,
                            unit_price=formatLang(self.env, order_line.price_unit, currency_obj=order.currency_id),
                        )
                    else:
                        account = self._get_computed_account(order, order_line.product_id, is_purchase)
                        amount_currency = order_line.untaxed_amount_to_invoice
                        amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
                        fnames = ['qty_to_invoice', 'untaxed_amount_to_invoice', 'qty_invoiced', 'qty_delivered', 'invoice_lines']
                        label = _(
                            '%(order)s - %(order_line)s; %(quantity_invoiced)s Invoiced, %(quantity_delivered)s Delivered at %(unit_price)s each',
                            order=order.name,
                            order_line=_ellipsis(order_line.name, 20),
                            quantity_invoiced=order_line.qty_invoiced,
                            quantity_delivered=order_line.qty_delivered,
                            unit_price=formatLang(self.env, order_line.price_unit, currency_obj=order.currency_id),
                        )
                    distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
                    values = _get_aml_vals(order, amount, amount_currency, account.id, label=label, analytic_distribution=distribution)
                    move_lines.append(Command.create(values))
                    total_balance += amount
                # must invalidate cache or o can mess when _create_invoices().action_post() of original order after this
                order.order_line.invalidate_model(fnames)

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
            body = _(
                'Accrual entry created on %(date)s: %(accrual_entry)s.\
                    And its reverse entry: %(reverse_entry)s.',
                date=self.date,
                accrual_entry=move._get_html_link(),
                reverse_entry=reverse_move._get_html_link(),
            )
            order.message_post(body=body)
        return {
            'name': _('Accrual Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', (move.id, reverse_move.id))],
        }
