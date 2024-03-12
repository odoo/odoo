# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

import pytz

from odoo import api, fields, models, _
from odoo.osv.expression import AND

class ReportSaleDetails(models.AbstractModel):

    _name = 'report.point_of_sale.report_saledetails'
    _description = 'Point of Sale Details'


    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        """ Serialise the orders of the requested time period, configs and sessions.
        :param date_start: The dateTime to start, default today 00:00:00.
        :type date_start: str.
        :param date_stop: The dateTime to stop, default date_start + 23:59:59.
        :type date_stop: str.
        :param config_ids: Pos Config id's to include.
        :type config_ids: list of numbers.
        :param session_ids: Pos Config id's to include.
        :type session_ids: list of numbers.
        :returns: dict -- Serialised sales.
        """
        domain = [('state', 'in', ['paid', 'invoiced', 'done'])]
        if (session_ids):
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC')).replace(tzinfo=None)

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain,
                [('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop))]
            ])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])

        orders = self.env['pos.order'].search(domain)

        if config_ids:
            config_currencies = self.env['pos.config'].search([('id', 'in', config_ids)]).mapped('currency_id')
        else:
            config_currencies = self.env['pos.session'].search([('id', 'in', session_ids)]).mapped('config_id.currency_id')
        # If all the pos.config have the same currency, we can use it, else we use the company currency
        if config_currencies and all(i == config_currencies.ids[0] for i in config_currencies.ids):
            user_currency = config_currencies[0]
        else:
            user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        refund_done = {}
        refund_taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += order.amount_total
            currency = order.session_id.currency_id

            for line in order.lines:
                if line.qty >= 0:
                    products_sold, taxes = self._get_products_and_taxes_dict(line, products_sold, taxes, currency)
                else:
                    refund_done, refund_taxes = self._get_products_and_taxes_dict(line, refund_done, refund_taxes, currency)

        taxes_info = self._get_taxes_info(taxes)
        refund_taxes_info = self._get_taxes_info(refund_taxes)

        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        if payment_ids:
            self.env.cr.execute("""
                SELECT method.id as id, payment.session_id as session, COALESCE(method.name->>%s, method.name->>'en_US') as name, method.is_cash_count as cash,
                     sum(amount) total, method.journal_id journal_id
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                    AND payment.id IN %s
                GROUP BY method.name, method.is_cash_count, payment.session_id, method.id, journal_id
            """, (self.env.lang, tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        configs = []
        sessions = []
        if config_ids:
            configs = self.env['pos.config'].search([('id', 'in', config_ids)])
            if session_ids:
                sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            else:
                sessions = self.env['pos.session'].search([('config_id', 'in', configs.ids), ('start_at', '>=', date_start), ('stop_at', '<=', date_stop)])
        else:
            sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            for session in sessions:
                configs.append(session.config_id)

        for payment in payments:
            payment['count'] = False

        for session in sessions:
            cash_counted = 0
            if session.cash_register_balance_end_real:
                cash_counted = session.cash_register_balance_end_real
            is_cash_method = False
            for payment in payments:
                account_payments = self.env['account.payment'].search([('pos_session_id', '=', session.id)])
                if payment['session'] == session.id:
                    if not payment['cash']:
                        ref_value = "Closing difference in %s (%s)" % (payment['name'], session.name)
                        account_move = self.env['account.move'].search([("ref", "=", ref_value)], limit=1)
                        if account_move:
                            payment_method = self.env['pos.payment.method'].browse(payment['id'])
                            is_loss = any(l.account_id == payment_method.journal_id.loss_account_id for l in account_move.line_ids)
                            is_profit = any(l.account_id == payment_method.journal_id.profit_account_id for l in account_move.line_ids)
                            payment['final_count'] = payment['total']
                            payment['money_difference'] = -account_move.amount_total if is_loss else account_move.amount_total
                            payment['money_counted'] = payment['final_count'] + payment['money_difference']
                            payment['cash_moves'] = []
                            if is_profit:
                                move_name = 'Difference observed during the counting (Profit)'
                                payment['cash_moves'] = [{'name': move_name, 'amount': payment['money_difference']}]
                            elif is_loss:
                                move_name = 'Difference observed during the counting (Loss)'
                                payment['cash_moves'] = [{'name': move_name, 'amount': payment['money_difference']}]
                            payment['count'] = True
                        elif payment['id'] in account_payments.mapped('pos_payment_method_id.id'):
                            account_payment = account_payments.filtered(lambda p: p.pos_payment_method_id.id == payment['id'])
                            payment['final_count'] = payment['total']
                            payment['money_counted'] = sum(account_payment.mapped('amount'))
                            payment['money_difference'] = payment['money_counted'] - payment['final_count']
                            payment['cash_moves'] = []
                            if payment['money_difference'] > 0:
                                move_name = 'Difference observed during the counting (Profit)'
                                payment['cash_moves'] = [{'name': move_name, 'amount': payment['money_difference']}]
                            elif payment['money_difference'] < 0:
                                move_name = 'Difference observed during the counting (Loss)'
                                payment['cash_moves'] = [{'name': move_name, 'amount': payment['money_difference']}]
                            payment['count'] = True
                    else:
                        is_cash_method = True
                        previous_session = self.env['pos.session'].search([('id', '<', session.id), ('state', '=', 'closed'), ('config_id', '=', session.config_id.id)], limit=1)
                        payment['final_count'] = payment['total'] + previous_session.cash_register_balance_end_real + session.cash_real_transaction
                        payment['money_counted'] = cash_counted
                        payment['money_difference'] = payment['money_counted'] - payment['final_count']
                        cash_moves = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)])
                        cash_in_out_list = []
                        cash_in_count = 0
                        cash_out_count = 0
                        if session.cash_register_balance_start > 0:
                            cash_in_out_list.append({
                                'name': _('Cash Opening'),
                                'amount': session.cash_register_balance_start,
                            })
                        for cash_move in cash_moves:
                            if cash_move.amount > 0:
                                cash_in_count += 1
                                name = f'Cash in {cash_in_count}'
                            else:
                                cash_out_count += 1
                                name = f'Cash out {cash_out_count}'
                            if cash_move.move_id.journal_id.id == payment['journal_id']:
                                cash_in_out_list.append({
                                    'name': cash_move.payment_ref if cash_move.payment_ref else name,
                                    'amount': cash_move.amount
                                })
                        payment['cash_moves'] = cash_in_out_list
                        payment['count'] = True
            if not is_cash_method:
                cash_name = 'Cash ' + str(session.name)
                payments.insert(0, {
                    'name': cash_name,
                    'total': 0,
                    'final_count': session.cash_register_balance_start,
                    'money_counted': session.cash_register_balance_end_real,
                    'money_difference': session.cash_register_balance_end_real - session.cash_register_balance_start,
                    'cash_moves': [],
                    'count': True,
                    'session': session.id,
                })
        products = []
        refund_products = []
        for category_name, product_list in products_sold.items():
            category_dictionnary = {
                'name': category_name,
                'products': sorted([{
                    'product_id': product.id,
                    'product_name': product.name,
                    'code': product.default_code,
                    'quantity': qty,
                    'price_unit': price_unit,
                    'discount': discount,
                    'uom': product.uom_id.name,
                    'total_paid': product_total,
                    'base_amount': base_amount,
                } for (product, price_unit, discount), (qty, product_total, base_amount) in product_list.items()], key=lambda l: l['product_name']),
            }
            products.append(category_dictionnary)
        products = sorted(products, key=lambda l: str(l['name']))

        for category_name, product_list in refund_done.items():
            category_dictionnary = {
                'name': category_name,
                'products': sorted([{
                    'product_id': product.id,
                    'product_name': product.name,
                    'code': product.default_code,
                    'quantity': qty,
                    'price_unit': price_unit,
                    'discount': discount,
                    'uom': product.uom_id.name,
                    'total_paid': product_total,
                    'base_amount': base_amount,
                } for (product, price_unit, discount), (qty, product_total, base_amount) in product_list.items()], key=lambda l: l['product_name']),
            }
            refund_products.append(category_dictionnary)
        refund_products = sorted(refund_products, key=lambda l: str(l['name']))

        products, products_info = self._get_total_and_qty_per_category(products)
        refund_products, refund_info = self._get_total_and_qty_per_category(refund_products)

        currency = {
            'symbol': user_currency.symbol,
            'position': True if user_currency.position == 'after' else False,
            'total_paid': user_currency.round(total),
            'precision': user_currency.decimal_places,
        }

        session_name = False
        if len(sessions) == 1:
            state = sessions[0].state
            date_start = sessions[0].start_at
            date_stop = sessions[0].stop_at
            session_name = sessions[0].name
        else:
            state = "multiple"

        config_names = []
        for config in configs:
            config_names.append(config.name)

        discount_number = 0
        discount_amount = 0
        invoiceList = []
        invoiceTotal = 0
        for session in sessions:
            discount_number += len(session.order_ids.filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0)))
            discount_amount += session.get_total_discount()
            invoiceList.append({
                'name': session.name,
                'invoices': session._get_invoice_total_list(),
            })
            invoiceTotal += session._get_total_invoice()

        return {
            'opening_note': sessions[0].opening_notes if len(sessions) == 1 else False,
            'closing_note': sessions[0].closing_notes if len(sessions) == 1 else False,
            'state': state,
            'currency': currency,
            'nbr_orders': len(orders),
            'date_start': date_start,
            'date_stop': date_stop,
            'session_name': session_name if session_name else False,
            'config_names': config_names,
            'payments': payments,
            'company_name': self.env.company.name,
            'taxes': list(taxes.values()),
            'taxes_info': taxes_info,
            'products': products,
            'products_info': products_info,
            'refund_taxes': list(refund_taxes.values()),
            'refund_taxes_info': refund_taxes_info,
            'refund_info': refund_info,
            'refund_products': refund_products,
            'discount_number': discount_number,
            'discount_amount': discount_amount,
            'invoiceList': invoiceList,
            'invoiceTotal': invoiceTotal,
        }

    def _get_products_and_taxes_dict(self, line, products, taxes, currency):
        key2 = (line.product_id, line.price_unit, line.discount)
        keys1 = line.product_id.product_tmpl_id.pos_categ_ids.mapped("name") or [_('Not Categorized')]
        for key1 in keys1:
            products.setdefault(key1, {})
            products[key1].setdefault(key2, [0.0, 0.0, 0.0])
            products[key1][key2][0] += line.qty
            products[key1][key2][1] += line.currency_id.round(line.price_unit * line.qty * (100 - line.discount) / 100.0)
            products[key1][key2][2] += line.price_subtotal

        if line.tax_ids_after_fiscal_position:
            line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
            base_amounts = {}
            for tax in line_taxes['taxes']:
                taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0})
                taxes[tax['id']]['tax_amount'] += tax['amount']
                base_amounts[tax['id']] = tax['base']

            for tax_id, base_amount in base_amounts.items():
                taxes[tax_id]['base_amount'] += base_amount
        else:
            taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0})
            taxes[0]['base_amount'] += line.price_subtotal_incl

        return products, taxes

    def _get_total_and_qty_per_category(self, categories):
        all_qty = 0
        all_total = 0
        for category_dict in categories:
            qty_cat = 0
            total_cat = 0
            for product in category_dict['products']:
                qty_cat += product['quantity']
                total_cat += product['base_amount']
            category_dict['total'] = total_cat
            category_dict['qty'] = qty_cat
        # IMPROVEMENT: It would be better if the `products` are grouped by pos.order.line.id.
        unique_products = list({tuple(sorted(product.items())): product for category in categories for product in category['products']}.values())
        all_qty = sum([product['quantity'] for product in unique_products])
        all_total = sum([product['base_amount'] for product in unique_products])

        return categories, {'total': all_total, 'qty': all_qty}

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        # initialize data keys with their value if provided, else None
        data.update({
            #If no data is provided it means that the report is called from the PoS, and docids represent the session_id
            'session_ids': data.get('session_ids') or (docids if not data.get('config_ids') and not data.get('date_start') and not data.get('date_stop') else None),
            'config_ids': data.get('config_ids'),
            'date_start': data.get('date_start'),
            'date_stop': data.get('date_stop')
        })
        configs = self.env['pos.config'].browse(data['config_ids'])
        data.update(self.get_sale_details(data['date_start'], data['date_stop'], configs.ids, data['session_ids']))
        return data

    def _get_taxes_info(self, taxes):
        total_tax_amount = 0
        total_base_amount = 0
        for tax in taxes.values():
            total_tax_amount += tax['tax_amount']
            total_base_amount += tax['base_amount']
        return {'tax_amount': total_tax_amount, 'base_amount': total_base_amount}
