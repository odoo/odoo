# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
import pytz
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from pytz import timezone
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    is_lock_screen = fields.Boolean(string="Lock Screen")

    def connection_check(self):
        return True

    def take_money_in_out(self, payload):
        for each in self:
            try:
                cash_out_obj = self.env['cash.box.out']
                bank_statements = [record.cash_register_id for record in each if record.cash_register_id]
                if not bank_statements:
                    raise Warning(_('There is no cash register for this PoS Session'))
                res = cash_out_obj.create({'name': payload.get('reason'), 'amount': payload.get('amount')})
                return res.with_context(active_model='pos.session', active_ids=[self.id])._run(bank_statements)
            except Exception as e:
                return {'error': 'There is no cash register for this PoS Session '}

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        partial_vals = {
            'account_id': payment.payment_method_id.receivable_account_id.id,
            'move_id': self.move_id.id,
            'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
        }
        if payment.payment_method_id.jr_use_for == 'wallet':
            partial_vals.update({
                'account_id': self.config_id.wallet_account_id.id,
                'is_wallet': True
            })
        if payment.payment_method_id.jr_use_for == 'gift_card':
            partial_vals.update({
                'account_id': self.config_id.gift_card_account_id.id,
            })
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = {
            'account_id': payment_method.receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name)
        }
        if payment_method.jr_use_for == 'gift_card':
            partial_vals.update({
                'account_id': self.config_id.gift_card_account_id.id,
            })
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _prepare_line(self, order_line):
        res = super(PosSession, self)._prepare_line(order_line)
        if self.config_id.enable_gift_card and (order_line.product_id.id == self.config_id.gift_card_product_id.id):
            res.update({
                'income_account_id': self.config_id.gift_card_account_id.id,
            })
        return res

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        combine_receivables = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_return = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        wallet_vals = []
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        wallet_difference = {'amount': 0.0, 'amount_converted': 0.0}
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
        for order in self.order_ids:
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            for payment in order.payment_ids:
                amount, date = payment.amount, payment.payment_date
                if payment.payment_method_id.split_transactions:
                    if payment.payment_method_id.is_cash_count:
                        split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment],
                                                                               {'amount': amount}, date)
                    else:
                        split_receivables[payment] = self._update_amounts(split_receivables[payment],
                                                                          {'amount': amount}, date)
                else:
                    key = payment.payment_method_id
                    if payment.payment_method_id.is_cash_count:
                        combine_receivables_cash[key] = self._update_amounts(combine_receivables_cash[key],
                                                                             {'amount': amount}, date)
                    else:
                        combine_receivables[key] = self._update_amounts(combine_receivables[key], {'amount': amount},
                                                                        date)

            if order.is_invoiced:
                # Combine invoice receivable lines
                key = order.partner_id
                if self.config_id.cash_rounding:
                    invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': order.amount_paid}, order.date_order)
                else:
                    invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': order.amount_total}, order.date_order)
                # side loop to gather receivable lines by account for reconciliation
                for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable' and not aml.reconciled):
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
            else:
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    if self.config_id.enable_wallet and (order_line.product_id.id == self.config_id.wallet_product.id):
                        amount = order_line.price_subtotal_incl
                        amount_converted = self.company_id.currency_id.round(order_line.price_subtotal_incl)
                        wallet_vals.append(self._get_wallet_credit_vals(amount, amount_converted, order_line.order_id))
                    else:
                        line = self._prepare_line(order_line)
                        sale_key = (
                            line['income_account_id'],
                            -1 if line['amount'] < 0 else 1,
                            tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in
                                  line['taxes']),
                            line['base_tags'],
                        )
                        sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']},
                                                               line['date_order'])
                        # Combine tax lines
                        for tax in line['taxes']:
                            tax_key = (tax['account_id'], tax['tax_repartition_line_id'], tax['id'],
                                       tuple(tax['tag_ids']))
                            order_taxes[tax_key] = self._update_amounts(
                                order_taxes[tax_key],
                                {'amount': tax['amount'], 'base_amount': tax['base']},
                                tax['date_order'],
                                round=not rounded_globally
                            )
                for tax_key, amounts in order_taxes.items():
                    if rounded_globally:
                        amounts = self._round_amounts(amounts)
                    for amount_key, amount in amounts.items():
                        taxes[tax_key][amount_key] += amount

                if self.company_id.anglo_saxon_accounting and order.picking_ids.ids:
                    # Combine stock lines
                    stock_moves = self.env['stock.move'].search([
                        ('picking_id', 'in', order.picking_ids.ids),
                        ('company_id.anglo_saxon_accounting', '=', True),
                        ('product_id.categ_id.property_valuation', '=', 'real_time')
                    ])
                    for move in stock_moves:
                        exp_key = move.product_id._get_product_accounts()['expense']
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        amount = -sum(move.sudo().stock_valuation_layer_ids.mapped('value'))
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount},
                                                                      move.picking_id.date, force_company_currency=True)
                        if move.location_id.usage == 'customer':
                            stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount},
                                                                         move.picking_id.date,
                                                                         force_company_currency=True)
                        else:
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
                                                                         move.picking_id.date,
                                                                         force_company_currency=True)

                if order.change_amount_for_wallet > self.company_id.currency_id.round(0.0):
                    # wallet_amount['amount'] = order.change_amount_for_wallet
                    wallet_difference = self._update_amounts(wallet_difference,
                                                             {'amount': order.change_amount_for_wallet},
                                                             order.date_order)
                    wallet_difference['order_id'] = order

                if self.config_id.cash_rounding:
                    diff = order.amount_paid - order.amount_total - order.change_amount_for_wallet
                    rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)
                # Increasing current partner's customer_rank
                order.partner_id._increase_rank('customer_rank')

        if self.company_id.anglo_saxon_accounting:
            global_session_pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
            if global_session_pickings:
                stock_moves = self.env['stock.move'].search([
                    ('picking_id', 'in', global_session_pickings.ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                ])
                for move in stock_moves:
                    exp_key = move.product_id._get_product_accounts()['expense']
                    out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                    amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
                    stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount},
                                                                  move.picking_id.date)
                    if move.location_id.usage == 'customer':
                        stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount},
                                                                     move.picking_id.date)
                    else:
                        stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
                                                                     move.picking_id.date)
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        MoveLine.create(wallet_vals)
        data.update({
            'taxes': taxes,
            'sales': sales,
            'stock_expense': stock_expense,
            'split_receivables': split_receivables,
            'combine_receivables': combine_receivables,
            'split_receivables_cash': split_receivables_cash,
            'combine_receivables_cash': combine_receivables_cash,
            'invoice_receivables': invoice_receivables,
            'stock_return': stock_return,
            'stock_output': stock_output,
            'order_account_move_receivable_lines': order_account_move_receivable_lines,
            'rounding_difference': rounding_difference,
            'wallet_difference': wallet_difference,
            'MoveLine': MoveLine
        })
        return data

    def _get_wallet_credit_vals(self, amount, amount_converted, order):
        partial_args = {
            'name': 'Wallet Credit',
            'is_wallet': True,
            'move_id': self.move_id.id,
            'partner_id': order.partner_id._find_accounting_partner(order.partner_id).id,
            'account_id': self.config_id.wallet_account_id.id,
        }
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _create_non_reconciliable_move_lines(self, data):
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - stock expense
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        taxes = data.get('taxes')
        sales = data.get('sales')
        stock_expense = data.get('stock_expense')
        split_receivables = data.get('split_receivables')
        combine_receivables = data.get('combine_receivables')
        rounding_difference = data.get('rounding_difference')
        wallet_difference = data.get('wallet_difference')
        MoveLine = data.get('MoveLine')

        tax_vals = [
            self._get_tax_vals(key, amounts['amount'], amounts['amount_converted'], amounts['base_amount_converted'])
            for key, amounts in taxes.items() if amounts['amount']]
        # Check if all taxes lines have account_id assigned. If not, there are repartition lines of the tax that have no account_id.
        tax_names_no_account = [line['name'] for line in tax_vals if line['account_id'] == False]
        if len(tax_names_no_account) > 0:
            error_message = _(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s'
            ) % ', '.join(tax_names_no_account)
            raise UserError(error_message)
        rounding_vals = []
        wallet_vals = []

        if not float_is_zero(rounding_difference['amount'],
                             precision_rounding=self.currency_id.rounding) or not float_is_zero(
            rounding_difference['amount_converted'], precision_rounding=self.currency_id.rounding):
            rounding_vals = [self._get_rounding_difference_vals(rounding_difference['amount'],
                                                                rounding_difference['amount_converted'])]
        if not float_is_zero(wallet_difference['amount'],
                             precision_rounding=self.currency_id.rounding) or not float_is_zero(
            wallet_difference['amount_converted'], precision_rounding=self.currency_id.rounding):
            wallet_vals = [self._get_wallet_difference_vals(wallet_difference['order_id'], wallet_difference['amount'],
                                                            wallet_difference['amount_converted'])]

        MoveLine.create(
            tax_vals
            + [self._get_sale_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in
               sales.items()]
            + [self._get_stock_expense_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in
               stock_expense.items()]
            + [self._get_split_receivable_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in
               split_receivables.items()]
            + [self._get_combine_receivable_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts
               in combine_receivables.items()]
            + rounding_vals
            + wallet_vals
        )
        return data

    def _get_wallet_difference_vals(self, order, amount, amount_converted):
        if self.config_id.enable_wallet:
            partial_args = {
                'name': 'Wallet Credit',
                'is_wallet': True,
                'move_id': self.move_id.id,
                'partner_id': order.partner_id._find_accounting_partner(order.partner_id).id,
                'account_id': self.config_id.wallet_account_id.id,
            }
            return self._credit_amounts(partial_args, amount, amount_converted)

    # POS session Close 
    @api.model
    def send_email_z_report(self, id):
        email_id = ''
        try:
            session_obj = self.env['pos.session'].browse(id)
            template_id = session_obj.config_id.email_template_id.id
            for user in session_obj.config_id.users_ids:
                if user.partner_id.email:
                    email_id += user.partner_id.email + ","
            template_obj = self.env['mail.template'].browse(template_id).with_context(email_to=email_id)
            report_id = self.env['ir.actions.report'].search(
                [('report_name', '=', 'flexipharmacy.pos_z_report_template')])
            if template_obj and report_id:
                template_obj.write({
                    'report_name': 'Z Report',
                    'report_template': report_id.id
                })
                template_obj.send_mail(session_obj.id, force_send=True)
            else:
                _logger.error('Mail Template and Report not defined!')
        except Exception as e:
            _logger.error('Unable to send email for z report of session %s', e)

    def custom_close_pos_session(self):
        for session in self:
            if session.config_id.email_close_session_report:
                self.send_email_z_report(session.id)
            if not session.config_id.cash_control:
                session.action_pos_session_closing_control()
                return True
            if session.config_id.cash_control:
                session.action_pos_session_closing_control()
                return self._validate_session()

    def cash_control_line(self, vals):
        cash_line = []
        cashbox_end_id = False
        if vals:
            cashbox_end_id = self.env['account.bank.statement.cashbox'].create([{}])
            for data in vals:
                cash_line.append((0, 0, {
                    'coin_value': data.get('coin_value'),
                    'number': data.get('number_of_coins'),
                    'subtotal': data.get('subtotal'),
                    'cashbox_id': cashbox_end_id.id,
                }))
            cashbox_end_id.write({'cashbox_lines_ids': cash_line})
        for statement in self.statement_ids:
            statement.write({'cashbox_end_id': cashbox_end_id.id, 'balance_end_real': cashbox_end_id.total})
        return True

    def set_cashbox_opening(self, opening_balance):
        self.state = 'opened'
        self.cash_register_id.balance_start = opening_balance

    def get_gross_total(self):
        gross_total = 0.0
        for line in self.order_ids.mapped('lines'):
            gross_total += line.qty * (line.price_unit - line.product_id.standard_price)
        return gross_total

    def get_product_cate_total(self):
        balance_end_real = 0.0
        for line in self.order_ids.mapped('lines'):
            balance_end_real += (line.qty * line.price_unit)
        return balance_end_real

    def get_net_gross_total(self):
        net_gross_profit = self.get_gross_total() - self.get_total_tax()
        return net_gross_profit

    def get_product_name(self, category_id):
        if category_id:
            category_name = self.env['pos.category'].browse([category_id]).name
            return category_name

    def get_product_category(self):
        product_list = []
        for line in self.order_ids.mapped('lines'):
            product_list.append({
                'pos_categ_id': line.product_id.pos_categ_id and line.product_id.pos_categ_id.id or False,
                'price': (line.qty * line.price_unit)
            })
        return product_list

    def get_journal_amount(self):
        journal_list = []
        if self.statement_ids:
            for statement in self.statement_ids:
                journal_list.append({'journal_id': statement.journal_id and statement.journal_id.name or False,
                                     'ending_bal': statement.balance_end_real or 0.0})
        return journal_list

    def get_total_closing(self):
        return self.cash_register_balance_end_real

    def get_total_sales(self):
        total_price = 0.0
        for order in self.order_ids:
            total_price += sum([(line.qty * line.price_unit) for line in order.lines])
        return total_price

    def get_total_tax(self):
        total_tax = 0.0
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        total_tax += sum([order.amount_tax for order in pos_order_ids])
        return total_tax

    def get_vat_tax(self):
        taxes_info = []
        tax_list = [tax.id for order in self.order_ids for line in
                    order.lines.filtered(lambda line: line.tax_ids_after_fiscal_position) for tax in
                    line.tax_ids_after_fiscal_position]
        tax_list = list(set(tax_list))
        for tax in self.env['account.tax'].browse(tax_list):
            total_tax = 0.00
            net_total = 0.00
            order_lines = self.env['pos.order.line'].search([('order_id', 'in', self.order_ids.ids)]).filtered(
                lambda line: tax in line.tax_ids_after_fiscal_position)
            for line in order_lines:
                total_tax += line.price_subtotal * tax.amount / 100
                net_total += line.price_subtotal
            taxes_info.append({
                'tax_name': tax.name,
                'tax_total': total_tax,
                'tax_per': tax.amount,
                'net_total': net_total,
                'gross_tax': total_tax + net_total
            })
        return taxes_info

    def get_total_discount(self):
        total_discount = 0.0
        for order in self.order_ids:
            total_discount += sum([((line.qty * line.price_unit) * line.discount) / 100 for line in order.lines])
        return total_discount

    def get_total_first(self):
        total = (self.get_total_sales() + self.get_total_tax()) - (abs(self.get_total_discount()))
        return total

    def get_session_date(self, date_time):
        if date_time:
            if self._context and self._context.get('tz'):
                tz = timezone(self._context.get('tz'))
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            if sign == '+':
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) + \
                            timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) - \
                            timedelta(hours=hour_tz, minutes=min_tz)
            return date_time.strftime('%d/%m/%Y %I:%M:%S %p')

    def get_session_time(self, date_time):
        if date_time:
            if self._context and self._context.get('tz'):
                tz = timezone(self._context.get('tz'))
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            if sign == '+':
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) + \
                            timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = datetime.strptime(str(date_time), DEFAULT_SERVER_DATETIME_FORMAT) - \
                            timedelta(hours=hour_tz, minutes=min_tz)
            return date_time.strftime('%I:%M:%S %p')

    def get_current_date(self):
        if self._context and self._context.get('tz'):
            tz = timezone(self._context['tz'])
        else:
            tz = pytz.utc
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%d/%m/%Y')
        else:
            return date.today().strftime('%d/%m/%Y')

    def get_current_time(self):
        if self._context and self._context.get('tz'):
            tz = timezone(self._context['tz'])
        else:
            tz = pytz.utc
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%I:%M %p')
        else:
            return datetime.now().strftime('%I:%M:%S %p')

    def get_pos_name(self):
        if self and self.config_id:
            return self.config_id.name

    def get_current_date_x(self):
        if self._context and self._context.get('tz'):
            tz = self._context['tz']
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%d/%m/%Y')
        else:
            return date.today().strftime('%d/%m/%Y')

    def get_current_time_x(self):
        if self._context and self._context.get('tz'):
            tz = self._context['tz']
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%I:%M %p')
        else:
            return datetime.now().strftime('%I:%M:%S %p')

    def auto_close_pos_session(self):
        enable_auto_close_session = self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.enable_auto_close_session')
        if enable_auto_close_session:
            session_ids = self.search([('state', 'in', ['opened', 'closing_control'])])
            for cash_control_session in session_ids.filtered(lambda session_id: session_id.config_id.cash_control):
                # cash_control_session.action_pos_session_closing_control()
                cashbox_end_id = self.env['account.bank.statement.cashbox'].create([{}])
                cash_line = [(0, 0, {
                    'coin_value': 1,
                    'number': cash_control_session.cash_register_balance_end,
                    'subtotal': cash_control_session.cash_register_balance_end,
                    'cashbox_id': cashbox_end_id.id,
                })]
                cashbox_end_id.write({'cashbox_lines_ids': cash_line,})
                for statement in cash_control_session.statement_ids:
                    statement.write({'cashbox_end_id': cashbox_end_id.id, 'balance_end_real': cash_control_session.cash_register_balance_end})
                cash_control_session._compute_cash_balance()
                cash_control_session.write({'stop_at': fields.Datetime.now()})
                cash_control_session.action_pos_session_validate()
            for cash_control_session in session_ids.filtered(lambda session_id: not session_id.config_id.cash_control):
                cash_control_session.action_pos_session_closing_control()
    
    def get_inventory_details(self):
        product_product = self.env['product.product']
        stock_location = self.config_id.picking_type_id.default_location_src_id
        inventory_records = []
        final_list = []
        product_details = []
        if self and self.id:
            for order in self.order_ids:
                for line in order.lines:
                    product_details.append({
                        'id': line.product_id.id,
                        'qty': line.qty,
                    })
        custom_list = []
        for each_prod in product_details:
            if each_prod.get('id') not in [x.get('id') for x in custom_list]:
                custom_list.append(each_prod)
            else:
                for each in custom_list:
                    if each.get('id') == each_prod.get('id'):
                        each.update({'qty': each.get('qty') + each_prod.get('qty')})
        for each in custom_list:
            product_id = product_product.browse(each.get('id'))
            if product_id:
                inventory_records.append({
                    'product_id': [product_id.id, product_id.name],
                    'category_id': [product_id.id, product_id.categ_id.name],
                    'used_qty': each.get('qty'),
                    'quantity': product_id.with_context(
                        {'location': stock_location.id, 'compute_child': False}).qty_available,
                    'uom_name': product_id.uom_id.name or ''
                })
            if inventory_records:
                temp_list = []
                temp_obj = []
                for each in inventory_records:
                    if each.get('product_id')[0] not in temp_list:
                        temp_list.append(each.get('product_id')[0])
                        temp_obj.append(each)
                    else:
                        for rec in temp_obj:
                            if rec.get('product_id')[0] == each.get('product_id')[0]:
                                qty = rec.get('quantity') + each.get('quantity')
                                rec.update({'quantity': qty})
                final_list = sorted(temp_obj, key=lambda k: k['quantity'])
        return final_list or []
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
