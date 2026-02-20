# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

import pytz

from odoo import api, fields, models, _
from odoo.fields import Domain
from odoo.tools import SQL


class ReportPoint_Of_SaleReport_Saledetails(models.AbstractModel):
    _name = 'report.point_of_sale.report_saledetails'

    _description = 'Point of Sale Details'

    def _get_date_start_and_date_stop(self, date_start, date_stop):
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = self.env.tz
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

        return date_start, date_stop

    def _get_domain(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        domain = Domain('state', 'in', ['paid', 'done'])

        if (session_ids):
            domain &= Domain('session_id', 'in', session_ids)
        else:
            date_start, date_stop = self._get_date_start_and_date_stop(date_start, date_stop)

            domain &= Domain('date_order', '>=', fields.Datetime.to_string(date_start))
            domain &= Domain('date_order', '<=', fields.Datetime.to_string(date_stop))

            if config_ids:
                domain &= Domain('config_id', 'in', config_ids)

        return domain

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
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
        if not session_ids:
            date_start, date_stop = self._get_date_start_and_date_stop(date_start, date_stop)

        domain = self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
        PosOrder = self.env['pos.order']

        order_query = PosOrder._search(domain)
        orders = PosOrder.browse(order_query)
        PosSession = self.env['pos.session']

        if config_ids:
            currency_ids = self.env['pos.config'].browse(config_ids).mapped('currency_id.id')
            configs = self.env['pos.config'].browse(config_ids)
            currency_ids = configs.mapped('currency_id.id')

            if session_ids:
                sessions = PosSession.browse(session_ids)
            else:
                sessions = PosSession.search([
                    ('config_id', 'in', configs.ids),
                    ('start_at', '>=', date_start),
                    ('stop_at', '<=', date_stop)
                ])
        else:
            currency_ids = PosSession.browse(session_ids).mapped('config_id.currency_id.id')
            sessions = PosSession.browse(session_ids)
            currency_ids = sessions.mapped('config_id.currency_id.id')
            configs = sessions.config_id

        # If all the pos.config have the same currency, we can use it, else we use the company currency
        if len(set(currency_ids)) == 1:
            currency_id = self.env['res.currency'].browse(currency_ids[0])
        else:
            currency_id = self.env.company.currency_id

        total = 0.0
        for o in orders:
            pricelist_currency = o.pricelist_id.currency_id
            total += pricelist_currency._convert(
                o.amount_total, currency_id, o.company_id, o.date_order or fields.Date.today()
            ) if pricelist_currency != currency_id else o.amount_total

        PosOrderLine = self.env['pos.order.line']
        line_ids = PosOrderLine._search([('order_id', 'in', order_query)])

        lines = PosOrderLine.browse(line_ids).with_prefetch(line_ids)

        products_sold = {}
        taxes = {'base_amount': 0.0, 'taxes': {}}
        refund_done = {}
        refund_taxes = {'base_amount': 0.0, 'taxes': {}}

        for line in lines:
            currency = line.currency_id
            if not line.order_id.is_refund:
                products_sold, taxes = self._get_products_and_taxes_dict(line, products_sold, taxes, currency)
            else:
                refund_done, refund_taxes = self._get_products_and_taxes_dict(line, refund_done, refund_taxes, currency)

        taxes_info = self._get_taxes_info(taxes)
        refund_taxes_info = self._get_taxes_info(refund_taxes)
        PosPaymentMethod = self.env['pos.payment.method']

        if payment_ids := self.env['pos.payment'].search([('pos_order_id', 'in', order_query)]).ids:
            method_name = PosPaymentMethod._field_to_sql('method', 'name')
            self.env.cr.execute(SQL("""
                SELECT method.id as id, payment.session_id as session, %(method_name)s as name, method.is_cash_count as cash,
                     sum(amount) total, method.journal_id journal_id
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                    AND payment.id IN %(payment_ids)s
                GROUP BY method.name, method.is_cash_count, payment.session_id, method.id, journal_id
                ORDER BY method.id, payment.session_id
            """, method_name=method_name, payment_ids=tuple(payment_ids)))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        AccountPayment = self.env['account.payment']
        Move = self.env['account.move']
        StatementLine = self.env['account.bank.statement.line']

        payments_by_session = {
            session.id: account_payments
            for session, account_payments in AccountPayment._read_group(
                [('pos_session_id', 'in', sessions.ids)],
                ['pos_session_id'],
                ['id:recordset'],
            )
        }

        move_refs = []
        for s in sessions:
            for p in payments:
                if p.get('session') == s.id:
                    p['count'] = False
                    ref = f"Closing difference in {p['name']} ({s.name})"
                    move_refs.append(ref)

        moves_by_ref = dict(Move._read_group(
            [('ref', 'in', move_refs)],
            ['ref'],
            ['id:recordset'],
        ))

        cash_moves_by_session = {
            session.id: lines
            for session, lines in StatementLine._read_group(
                [('pos_session_id', 'in', sessions.ids)],
                ['pos_session_id'],
                ['id:recordset'],
            )
        }

        for session in sessions:
            cash_counted = session.cash_register_balance_end_real or 0
            related_moves = cash_moves_by_session.get(session.id, [])
            is_cash_method = False
            for p in payments:
                if p['session'] != session.id:
                    continue

                if p['cash']:
                    is_cash_method = True
                    p['final_count'] = p['total'] + session.cash_register_balance_start + session.cash_real_transaction
                    p['money_counted'] = cash_counted
                    p['money_difference'] = p['money_counted'] - p['final_count']

                    slist = []
                    if session.cash_register_balance_start:
                        slist.append({'name': _('Cash Opening'), 'amount': session.cash_register_balance_start})

                    in_count = 0
                    out_count = 0
                    for m in related_moves:
                        name = m.payment_ref or (f"Cash in {in_count + 1}" if m.amount > 0 else f"Cash out {out_count + 1}")
                        slist.append({'name': name, 'amount': m.amount})
                        if m.amount > 0:
                            in_count += 1
                        else:
                            out_count += 1

                    p['cash_moves'] = slist
                    p['count'] = True
                    continue

                ref = f"Closing difference in {p['name']} ({session.name})"
                move = moves_by_ref.get(ref)

                if move:
                    pm = PosPaymentMethod.browse(p['id'])
                    loss = any(l.account_id == pm.journal_id.loss_account_id for l in move.line_ids)
                    profit = any(l.account_id == pm.journal_id.profit_account_id for l in move.line_ids)

                    p['final_count'] = p['total']
                    p['money_difference'] = -move.amount_total if loss else move.amount_total
                    p['money_counted'] = p['final_count'] + p['money_difference']
                    p['cash_moves'] = []
                    if p['money_difference'] != 0:
                        p['cash_moves'] = [{
                            'name': 'Difference observed during the counting (Profit)' if profit else 'Difference observed during the counting (Loss)',
                            'amount': p['money_difference']
                        }]
                    p['count'] = True
                    continue

                aps = payments_by_session.get(session.id, [])
                aps = [a for a in aps if a.pos_payment_method_id.id == p['id']]
                if aps:
                    p['final_count'] = p['total']
                    p['money_counted'] = sum(a.amount_signed for a in aps)
                    p['money_difference'] = p['money_counted'] - p['final_count']
                    name = "Profit" if p['money_difference'] > 0 else "Loss"
                    p['cash_moves'] = []
                    if p['money_difference'] != 0:
                        p['cash_moves'] = [{'name': f"Difference observed during the counting ({name})", 'amount': p['money_difference']}]
                    p['count'] = True
            if not is_cash_method:
                cash_name = _('Cash %(session_name)s', session_name=session.name)
                previous_session = PosSession.search([('id', '<', session.id), ('state', '=', 'closed'), ('config_id', '=', session.config_id.id)], limit=1)
                final_count = previous_session.cash_register_balance_end_real + session.cash_real_transaction
                cash_difference = session.cash_register_balance_end_real - final_count
                cash_moves = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)], order='date asc')
                cash_in_out_list = []

                if previous_session.cash_register_balance_end_real > 0:
                    cash_in_out_list.append({
                        'name': _('Cash Opening'),
                        'amount': previous_session.cash_register_balance_end_real,
                    })

                # If there is a cash difference, we remove the last cash move which is the cash difference
                if session.currency_id.round(cash_difference) != 0:
                    cash_moves = cash_moves[:-1]

                for cash_move in cash_moves:
                    cash_in_out_list.append({
                        'name': cash_move.payment_ref,
                        'amount': cash_move.amount
                    })
                payments.insert(0, {
                    'name': cash_name,
                    'total': 0,
                    'final_count': final_count,
                    'money_counted': session.cash_register_balance_end_real,
                    'money_difference': cash_difference,
                    'cash_moves': cash_in_out_list,
                    'count': True,
                    'session': session.id,
                })

        products = [
            {
                'name': cat,
                'products': sorted([
                    {
                        'product_id': p.id,
                        'product_name': p.display_name,
                        'barcode': p.barcode,
                        'quantity': qty,
                        'price_unit': price_unit,
                        'discount': discount,
                        'uom': p.uom_id.name,
                        'total_paid': total_paid,
                        'base_amount': base_amount,
                        'combo_products_label': combo_products_label,
                    }
                    for (p, price_unit, discount), (qty, total_paid, base_amount, combo_products_label)
                    in plist.items()
                ], key=lambda x: x['product_name'])
            }
            for cat, plist in sorted(products_sold.items(), key=lambda x: x[0])
        ]

        refund_products = [
            {
                'name': cat,
                'products': sorted([
                    {
                        'product_id': p.id,
                        'product_name': p.display_name,
                        'barcode': p.barcode,
                        'quantity': qty,
                        'price_unit': price_unit,
                        'discount': discount,
                        'uom': p.uom_id.name,
                        'total_paid': total_paid,
                        'base_amount': base_amount,
                        'combo_products_label': combo_products_label,
                    }
                    for (p, price_unit, discount), (qty, total_paid, base_amount, combo_products_label)
                    in plist.items()
                ], key=lambda x: x['product_name'])
            }
            for cat, plist in sorted(refund_done.items(), key=lambda x: x[0])
        ]

        products, products_info = self.with_context(config_id=configs[:1].id if configs else False)._get_total_and_qty_per_category(products)
        refund_products, refund_info = self.with_context(config_id=configs[:1].id if configs else False)._get_total_and_qty_per_category(refund_products)

        discount_number = len(lines.filtered(lambda l: l.discount > 0))
        discount_amount = sum(l._get_discount_amount() for l in lines.filtered(lambda l: l.discount > 0))

        pos_session_name = False
        if len(sessions) == 1:
            state = sessions[0].state
            date_start = sessions[0].start_at
            date_stop = sessions[0].stop_at
            pos_session_name = sessions[0].name
        else:
            state = "multiple"

        config_names = configs.mapped('name')

        invoiceList = []
        invoiceTotal = 0
        totalPaymentsAmount = 0

        for session in sessions:
            invoiceList.append({
                'name': session.name,
                'invoices': session._get_invoice_total_list(),
            })
            invoiceTotal += session._get_total_invoice()
            totalPaymentsAmount += session.total_payments_amount
        payments_per_method = {}
        payment_method_set = set()
        session_set = set()
        for p in payments:
            if p.get('id'):
                payment_method_set.add(p['id'])
            if p.get('session'):
                session_set.add(p['session'])
        payment_method_name_by_id = {
            pm.id: pm.name
            for pm in PosPaymentMethod.browse(payment_method_set)
        }
        session_name_by_id = {
            s.id: s.name
            for s in PosSession.browse(session_set)
        }
        payments_per_method = {}
        for p in payments:
            pid = p.get('id')
            if not pid:
                continue
            method_name = payment_method_name_by_id.get(pid)
            session_name = session_name_by_id.get(p['session'])
            p['name'] = f"{method_name} {session_name}"
            payments_per_method.setdefault(pid, {
                'name': method_name,
                'total': 0,
            })
            payments_per_method[pid]['total'] += p['total']

        return {
            'opening_note': sessions[0].opening_notes if len(sessions) == 1 else False,
            'closing_note': sessions[0].closing_notes if len(sessions) == 1 else False,
            'state': state,
            'currency': {
                'symbol': currency_id.symbol,
                'position': currency_id.position == 'after',
                'total_paid': total,
                'precision': currency_id.decimal_places,
            },
            'nbr_orders': len(order_query),
            'date_start': date_start,
            'date_stop': date_stop,
            'session_name': pos_session_name or False,
            'config_names': config_names,
            'payments': payments,
            'company_name': self.env.company.name,
            'taxes': list(taxes['taxes'].values()),
            'taxes_info': taxes_info,
            'products': products,
            'products_info': products_info,
            'refund_taxes': list(refund_taxes['taxes'].values()),
            'refund_taxes_info': refund_taxes_info,
            'refund_info': refund_info,
            'refund_products': refund_products,
            'discount_number': discount_number,
            'discount_amount': discount_amount,
            'invoiceList': invoiceList,
            'invoiceTotal': invoiceTotal,
            'total_paid': totalPaymentsAmount,
            'payments_per_method': payments_per_method.values(),
            'show_payment_per_method': not session_ids,
        }

    def _get_product_total_amount(self, line):
        return line.currency_id.round(line.price_unit * line.qty * (100 - line.discount) / 100.0)

    def _get_products_and_taxes_dict(self, line, products, taxes, currency):
        key2 = (line.product_id, line.price_unit, line.discount)
        key1 = line.product_id.product_tmpl_id.pos_categ_ids[0].name if len(line.product_id.product_tmpl_id.pos_categ_ids) else _('Not Categorized')
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        products.setdefault(key1, {})
        products[key1].setdefault(key2, [0.0, 0.0, 0.0, ''])
        products[key1][key2][0] = round(products[key1][key2][0] + abs(line.qty), precision)
        products[key1][key2][1] += self._get_product_total_amount(line)
        products[key1][key2][2] += line.price_subtotal

        # Name of each combo products along with the combo
        if line.combo_line_ids:
            combo_products_label = ' (' + ", ".join(line.combo_line_ids.product_id.mapped('name')) + ')'
            products[key1][key2][3] = combo_products_label

        if line.tax_ids_after_fiscal_position:
            line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
            base_amounts = {}
            for tax in line_taxes['taxes']:
                taxes['taxes'].setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0})
                taxes['taxes'][tax['id']]['tax_amount'] += tax['amount']
                base_amounts[tax['id']] = tax['base']

            for tax_id, base_amount in base_amounts.items():
                taxes['taxes'][tax_id]['base_amount'] += currency.round(base_amount)
        else:
            taxes['taxes'].setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0})
            taxes['taxes'][0]['base_amount'] += line.price_subtotal_incl

        refund_sign = -1 if line.order_id.is_refund else 1
        taxes['base_amount'] += line.price_subtotal * refund_sign
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

    def _prepare_get_sale_details_args_kwargs(self, data):
        configs = self.env['pos.config'].browse(data['config_ids'])
        args = (data['date_start'], data['date_stop'], configs.ids, data['session_ids'])
        kwargs = {}
        return args, kwargs

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        # initialize data keys with their value if provided, else None
        data.update({
            #If no data is provided it means that the report is called from the PoS, and docids represent the session_id
            'session_ids': data.get('session_ids') or (docids if not data.get('config_ids') and not data.get('date_start') and not data.get('date_stop') else None),
            'config_ids': data.get('config_ids'),
            'date_start': data.get('date_start'),
            'date_stop': data.get('date_stop'),
        })
        args, kwargs = self._prepare_get_sale_details_args_kwargs(data)
        data.update(self.get_sale_details(*args, **kwargs))
        return data

    def _get_taxes_info(self, taxes):
        total_tax_amount = 0
        total_base_amount = taxes['base_amount']
        for tax in taxes['taxes'].values():
            total_tax_amount += tax['tax_amount']
        return {'tax_amount': total_tax_amount, 'base_amount': total_base_amount}
