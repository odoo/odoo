from collections import defaultdict

from odoo import _, api, models
from odoo.fields import Domain
from odoo.tools import SQL

from .pos_report_handler import report_section


class PosSalesDetailReport(models.AbstractModel):
    _name = 'pos.sales.detail.report'
    _inherit = 'pos.report.handler'
    _description = 'POS Sales Detail Report Handler'

    def _get_filters(self):
        return [
            {'type': 'date_range', 'default': 'month'},
            {'type': 'multi_select', 'key': 'config_ids', 'model': 'pos.config', 'label': 'Point of Sale'},
            {'type': 'single_select', 'key': 'session_id', 'model': 'pos.session', 'label': 'Session'},
        ]

    def _get_report_name(self, default_name):
        session = self.env['pos.session'].browse(self.env.context.get('session_id'))
        if not session:
            return super()._get_report_name(default_name)
        return 'Daily Sales Report %s' % ('Z' if session.state == 'closed' else 'X')

    def _get_pdf_templates(self):
        templates = super()._get_pdf_templates()
        if self.env.ref('point_of_sale.pos_sales_detail_pdf_data_row', raise_if_not_found=False):
            templates = {**templates, 'data_row': 'point_of_sale.pos_sales_detail_pdf_data_row'}
        return templates

    _xlsx_product_columns = [
        {'id': 'uom', 'label': 'UoM', 'type': 'string', 'align': 'left'},
        {'id': 'discount', 'label': 'Disc', 'type': 'string', 'align': 'right'},
        {'id': 'combo_label', 'label': 'Combo', 'type': 'string', 'align': 'left'},
    ]

    def _get_xlsx_section_columns(self, section):
        columns = super()._get_xlsx_section_columns(section)
        if section.get('section_id') in ('sales', 'refunds'):
            return self._xlsx_product_columns + columns
        return columns

    def _get_xlsx_row_value(self, line, column):
        value = super()._get_xlsx_row_value(line, column)
        if column.get('id') == 'discount' and value:
            return f"{value}%"
        return value

    def _get_sections_columns(self):
        return {
            'sales': [
                {'id': 'qty', 'label': _('Qty'), 'type': 'integer', 'align': 'right'},
                {'id': 'amount_total', 'label': _('Total'), 'type': 'monetary', 'align': 'right'},
            ],
            'refunds': [
                {'id': 'qty', 'label': _('Qty'), 'type': 'integer', 'align': 'right'},
                {'id': 'amount_total', 'label': _('Total'), 'type': 'monetary', 'align': 'right'},
            ],
            'taxes_sales': [
                {'id': 'tax_amount', 'label': _('Tax'), 'type': 'monetary', 'align': 'right'},
                {'id': 'base_amount', 'label': _('Base'), 'type': 'monetary', 'align': 'right'},
                {'id': 'amount_total', 'label': _('Total'), 'type': 'monetary', 'align': 'right'},
            ],
            'taxes_refunds': [
                {'id': 'tax_amount', 'label': _('Tax'), 'type': 'monetary', 'align': 'right'},
                {'id': 'base_amount', 'label': _('Base'), 'type': 'monetary', 'align': 'right'},
                {'id': 'amount_total', 'label': _('Total'), 'type': 'monetary', 'align': 'right'},
            ],
            'payments': [
                {'id': 'amount_total', 'label': _('Amount'), 'type': 'monetary', 'align': 'right'},
            ],
            'discounts': [
                {'id': 'count', 'label': _('Count'), 'type': 'integer', 'align': 'right'},
                {'id': 'amount', 'label': _('Amount'), 'type': 'monetary', 'align': 'right'},
            ],
            'invoices': [
                {'id': 'count', 'label': _('Count'), 'type': 'integer', 'align': 'right'},
                {'id': 'amount_total', 'label': _('Total'), 'type': 'monetary', 'align': 'right'},
            ],
            'session_control': [
                {'id': 'expected', 'label': _('Expected'), 'type': 'monetary', 'align': 'right'},
                {'id': 'counted', 'label': _('Counted'), 'type': 'monetary', 'align': 'right'},
                {'id': 'difference', 'label': _('Diff'), 'type': 'monetary', 'align': 'right'},
            ],
            'opening_notes': [
                {'id': 'note', 'label': _('Note'), 'type': 'string', 'align': 'left'},
            ],
            'closing_notes': [
                {'id': 'note', 'label': _('Note'), 'type': 'string', 'align': 'left'},
            ],
        }

    def _get_receipt_products(self, lines):
        qty_precision = self.env['decimal.precision'].precision_get('Product Unit')
        price_precision = self.env['decimal.precision'].precision_get('Product Price')

        categories = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
        for line in lines:
            category = line.product_id.product_tmpl_id.pos_categ_ids[:1]
            totals = categories[category.name or _('Not Categorized')][line.product_id]
            amount = line.currency_id.round(line.price_unit * line.qty * (100 - line.discount) / 100.0)
            totals[0] = round(totals[0] + abs(line.qty), qty_precision)
            totals[1] += amount

        return [
            {
                'name': name,
                'qty': round(sum(qty for qty, amount in products.values()), qty_precision),
                'total_paid': round(sum(amount for qty, amount in products.values()), price_precision),
                'products': sorted([
                    {
                        'product_id': product.id,
                        'product_name': product.display_name,
                        'quantity': qty,
                        'total_paid': amount,
                    }
                    for product, (qty, amount) in products.items()
                ], key=lambda p: p['product_name']),
            }
            for name, products in categories.items()
        ]

    def _get_receipt_taxes(self, lines):
        taxes = {}
        for line in lines:
            if not line.tax_ids_after_fiscal_position:
                taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0})
                continue
            computed = line.tax_ids_after_fiscal_position.sudo().compute_all(
                line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                line.currency_id, line.qty, product=line.product_id,
                partner=line.order_id.partner_id or False,
            )
            for tax in computed['taxes']:
                taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0})
                taxes[tax['id']]['tax_amount'] += tax['amount']
        return list(taxes.values())

    def _get_receipt_payments(self, orders):
        currency = self._get_currency()
        results = self.env['pos.payment']._read_group(
            [('pos_order_id', 'in', orders.ids)],
            ['session_id', 'payment_method_id'],
            ['amount:sum'],
        )

        totals = defaultdict(float)
        rows = {}
        sessions = orders.session_id
        cash_sessions = set()
        for session, method, amount in results:
            key = (session.id, method.id)
            if key not in rows:
                rows[key] = f'{method.name} {session.name}'
            totals[key] += amount
            if method.type == 'cash':
                cash_sessions.add(session.id)

        payments = [
            {'name': rows[key], 'total': currency.round(amount)}
            for key, amount in totals.items()
        ]

        for session in sessions:
            if session.id not in cash_sessions:
                payments.append({'name': _('Cash %(session_name)s', session_name=session.name), 'total': 0})

        return payments

    @api.model
    def get_sale_details_receipt_data(self):
        session = self.env['pos.session'].browse(self.env.context.get('session_id'))
        orders = self.env['pos.order'].search(self._get_order_domain())
        cancelled_orders = self.env['pos.order'].search(self._get_order_domain(states=('cancel',)))

        lines = orders.lines.filtered(lambda line: not self._is_discount_product(line))
        refund_lines = lines.filtered(lambda line: line.order_id.is_refund_or_negative())
        sold_lines = lines - refund_lines

        total_paid = sum(order.amount_total for order in orders)

        return {
            'products': self._get_receipt_products(sold_lines),
            'refund_products': self._get_receipt_products(refund_lines),
            'cancelled_products': self._get_receipt_products(cancelled_orders.lines),
            'taxes': self._get_receipt_taxes(sold_lines),
            'payments': self._get_receipt_payments(orders),
            'currency': {'total_paid': self._get_currency().round(total_paid)},
            'session_state': session.state if session else 'multiple',
        }

    def _get_currency(self):
        """Report display currency, cached for the current transaction."""
        config_ids = tuple(sorted(self.env.context.get('config_ids') or ()))
        session_id = self.env.context.get('session_id')
        key = ('pos_sales_detail_currency', config_ids, session_id, self.env.company.id)

        cache = self.env.cr.cache
        if key not in cache:
            if config_ids:
                currencies = self.env['pos.config'].browse(config_ids).mapped('currency_id')
            elif session_id:
                currencies = self.env['pos.session'].browse(session_id).mapped('config_id.currency_id')
            else:
                currencies = self.env['pos.config'].search([]).mapped('currency_id')

            currency = (
                currencies[0]
                if currencies and len(set(currencies.ids)) == 1
                else self.env.company.currency_id
            )
            cache[key] = currency.id

        return self.env['res.currency'].browse(cache[key])

    def _get_sale_line_totals_query(self, is_refund=False, group_fields=[], extra_domain=None):
        """Build the query for sale line totals."""
        domain = self._get_sale_line_domain(is_refund=is_refund)
        if extra_domain:
            domain &= Domain(extra_domain)

        query = self.env['pos.order.line']._search(domain)

        line_table = query.table
        order_table = line_table._join('order_id')
        config_table = order_table._join('config_id')

        group_by = [
            config_table['currency_id'],
            line_table['company_id'],
            SQL("CAST(%s AS date)", order_table['date_order']),
            *(line_table[field] for field in group_fields),
        ]
        query.groupby = SQL(", ").join(group_by)

        select = [
            SQL("COALESCE(SUM(ABS(%s)), 0.0)", line_table['qty']),
            SQL(
                "COALESCE(SUM(COALESCE(%s, 0.0) * COALESCE(%s, 0.0) "
                "* (100.0 - COALESCE(%s, 0.0)) / 100.0), 0.0)",
                line_table['price_unit'],
                line_table['qty'],
                line_table['discount'],
            ),
        ]

        return query, select, group_by

    def _get_sale_line_totals(self, is_refund=False, group_fields=[], extra_domain=None):
        """Get sale line totals grouped by the given field."""
        query, select, group_by = self._get_sale_line_totals_query(is_refund, group_fields, extra_domain)

        rows = self.env.execute_query(query.select(*select, *group_by))

        totals = defaultdict(lambda: [0.0, 0.0])
        for qty, amount, curr_id, comp_id, date_order, *group in rows:
            total = totals[group[0] if len(group) == 1 else tuple(group) if group else 'default']
            total[0] += qty
            total[1] += self._convert_to_report_currency(amount, curr_id, comp_id, date_order)
        return totals

    @report_section(id='sales', name='Sales', sequence=10, foldability="expanded")
    def _section_sales(self):
        qty, amount = self._get_sale_line_totals().get('default', [0.0, 0.0])

        return {
            'name': _('Sales'),
            'foldability': 'expanded' if (qty or amount) else 'static',
            'style': 'bold',
            'qty': qty,
            'amount_total': self._get_currency().round(amount),
        }

    @report_section(id='category', parent='sales')
    def _section_sales_categories(self):
        product_totals = self._get_sale_line_totals(group_fields=['product_id'])
        products = self.env['product.product'].browse(list(product_totals))

        names = {}
        totals = defaultdict(lambda: [0.0, 0.0])
        for product in products:
            category = product.product_tmpl_id.pos_categ_ids[:1]
            names[category.id or 0] = category.name or _('Not Categorized')
            qty, amount = product_totals[product.id]
            totals[category.id or 0][0] += qty
            totals[category.id or 0][1] += amount

        return [
            {
                'record_id': cid,
                'name': names[cid],
                'foldability': 'collapsed',
                'style': 'bold',
                'qty': totals[cid][0],
                'amount_total': self._get_currency().round(totals[cid][1]),
            }
            for cid in sorted(names, key=lambda cid: str(names[cid] or ''))
        ]

    @report_section(id='product', parent='category')
    def _section_sales_products(self):
        return self._build_product_lines(is_refund=False)

    @report_section(id='refunds', name='Refunds', sequence=15)
    def _section_refunds(self):
        qty, amount = self._get_sale_line_totals(is_refund=True).get('default', [0.0, 0.0])

        return {
            'name': _('Refunds'),
            'foldability': 'collapsed' if (qty or amount) else 'static',
            'style': 'bold',
            'qty': qty,
            'amount_total': self._get_currency().round(amount),
        }

    @report_section(id='refund_category', parent='refunds')
    def _section_refunds_categories(self):
        product_totals = self._get_sale_line_totals(is_refund=True, group_fields=['product_id'])
        products = self.env['product.product'].browse(list(product_totals))

        names = {}
        totals = defaultdict(lambda: [0.0, 0.0])
        for product in products:
            category = product.product_tmpl_id.pos_categ_ids[:1]
            names[category.id or 0] = category.name or _('Not Categorized')
            qty, amount = product_totals[product.id]
            totals[category.id or 0][0] += qty
            totals[category.id or 0][1] += amount

        return [
            {
                'record_id': cid,
                'name': names[cid],
                'foldability': 'collapsed',
                'style': 'bold',
                'qty': totals[cid][0],
                'amount_total': self._get_currency().round(totals[cid][1]),
            }
            for cid in sorted(names, key=lambda cid: str(names[cid] or ''))
        ]

    @report_section(id='refund_product', parent='refund_category')
    def _section_refunds_products(self):
        return self._build_product_lines(is_refund=True)

    def _build_product_lines(self, is_refund):
        category_id = self.env.context.get('record_id')
        category_domain = [
            ('product_id.product_tmpl_id.pos_categ_ids', '=', False)
            if not category_id
            else ('product_id.product_tmpl_id.pos_categ_ids', 'in', [category_id]),
        ]
        totals = self._get_sale_line_totals(
            is_refund=is_refund,
            group_fields=['product_id', 'price_unit', 'discount'],
            extra_domain=category_domain,
        )

        products = self.env['product.product'].browse({key[0] for key in totals})
        combo_lines = self.env['pos.order.line'].search(
            self._get_sale_line_domain(is_refund=is_refund)
            & Domain(category_domain)
            & Domain([('combo_line_ids', '!=', False)]),
        )

        combo_labels = {
            (line.product_id.id, line.price_unit, line.discount):
                ' (' + ', '.join(line.combo_line_ids.product_id.mapped('name')) + ')'
            for line in combo_lines
        }

        result = []
        for (product_id, price, discount), (qty, amount) in totals.items():
            product = products.browse(product_id)
            result.append({
                'record_id': f'{product_id}_{price}_{discount}'.replace('.', '_'),
                'name': product.display_name,
                'foldability': 'static',
                'style': 'normal',
                'qty': qty,
                'amount_total': self._get_currency().round(amount),
                'discount': discount,
                'uom': product.uom_id.name,
                'barcode': product.barcode or False,
                'combo_label': combo_labels.get((product_id, price, discount), ''),
            })

        return sorted(result, key=lambda line: line['name'])

    def _get_tax_totals(self, is_refund=False):
        """Aggregate tax base and tax amount from POS order lines."""
        query = self.env['pos.order.line']._search(self._get_sale_line_domain(is_refund=is_refund))

        line_table = query.table
        order_table = line_table._join('order_id')
        config_table = order_table._join('config_id')

        group_by = [
            config_table['currency_id'],
            line_table['company_id'],
            SQL("CAST(%s AS date)", order_table['date_order']),
        ]
        query.groupby = SQL(", ").join(group_by)

        select = [
            SQL("COALESCE(SUM(%s), 0.0)", line_table['price_subtotal']),
            SQL("COALESCE(SUM(%s), 0.0)", line_table['price_subtotal_incl']),
        ]

        rows = self.env.execute_query(query.select(*select, *group_by))

        base = 0.0
        tax = 0.0
        for subtotal, subtotal_incl, currency_id, company_id, date_order in rows:
            base += self._convert_to_report_currency(subtotal, currency_id, company_id, date_order)
            tax += self._convert_to_report_currency(subtotal_incl - subtotal, currency_id, company_id, date_order)

        if is_refund:
            base = abs(base)
            tax = abs(tax)

        return base, tax

    @report_section(id='taxes_sales', name='Taxes on Sales', sequence=20)
    def _section_taxes_sales(self):
        base, tax = self._get_tax_totals()
        return {
            'name': _('Taxes on Sales'),
            'foldability': 'collapsed',
            'style': 'bold',
            'tax_amount': tax,
            'base_amount': base,
            'amount_total': base + tax,
        }

    @report_section(id='tax_line', parent='taxes_sales')
    def _section_taxes_sales_lines(self):
        return self._build_tax_lines(is_refund=False)

    @report_section(id='taxes_refunds', name='Taxes on Refunds', sequence=25)
    def _section_taxes_refunds(self):
        base, tax = self._get_tax_totals(is_refund=True)
        return {
            'name': _('Taxes on Refunds'),
            'foldability': 'collapsed',
            'style': 'bold',
            'tax_amount': tax,
            'base_amount': base,
            'amount_total': base + tax,
        }

    @report_section(id='refund_tax_line', parent='taxes_refunds')
    def _section_taxes_refunds_lines(self):
        return self._build_tax_lines(is_refund=True)

    def _build_tax_lines(self, is_refund):
        domain = self._get_sale_line_domain(is_refund=is_refund)
        lines = self.env['pos.order.line'].search(domain)
        currency = self._get_currency()
        taxes = {}
        for line in lines:
            if self._is_discount_product(line):
                continue
            if line.tax_ids_after_fiscal_position:
                computed = line.tax_ids_after_fiscal_position.sudo().compute_all(
                    line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                    currency, abs(line.qty), product=line.product_id,
                    partner=line.order_id.partner_id or False,
                )
                for tax in computed['taxes']:
                    taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0})
                    taxes[tax['id']]['tax_amount'] += tax['amount']
                    taxes[tax['id']]['base_amount'] += currency.round(tax['base'])
            else:
                taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0})
                taxes[0]['base_amount'] += line.price_subtotal_incl
        return [
            {
                'record_id': tid,
                'name': t['name'],
                'foldability': 'static',
                'style': 'normal',
                'tax_amount': t['tax_amount'],
                'base_amount': t['base_amount'],
                'amount_total': t['base_amount'] + t['tax_amount'],
            }
            for tid, t in taxes.items()
        ]

    @report_section(id='payments', name='Payments', sequence=30)
    def _section_payments(self):
        order_ids = self.env['pos.order'].search(self._get_order_domain()).ids
        if not order_ids:
            return {
                'name': _('Payments'),
                'foldability': 'static',
                'style': 'bold',
                'amount_total': 0.0,
            }

        payment_groups = self.env['pos.payment']._read_group(
            [('pos_order_id', 'in', order_ids)],
            ['pos_order_id.currency_id', 'pos_order_id.company_id', 'pos_order_id.date_order:day'],
            ['amount:sum'],
        )

        total = 0.0
        for currency, company, date_order, amount in payment_groups:
            total += self._convert_to_report_currency(amount, currency, company, date_order)

        return {
            'name': _('Payments'),
            'foldability': 'collapsed' if payment_groups else 'static',
            'style': 'bold',
            'amount_total': self._get_currency().round(total),
        }

    @report_section(id='payment_method', parent='payments')
    def _section_payments_methods(self):
        order_ids = self.env['pos.order'].search(self._get_order_domain()).ids
        if not order_ids:
            return []

        groups = self.env['pos.payment']._read_group(
            [('pos_order_id', 'in', order_ids)],
            [
                'session_id',
                'payment_method_id',
                'pos_order_id.currency_id',
                'pos_order_id.company_id',
                'pos_order_id.date_order:day',
            ],
            ['amount:sum'],
        )

        session_totals = defaultdict(float)
        method_totals = defaultdict(float)
        sessions = {}
        methods = {}

        for session, method, currency, company, date_order, amount in groups:
            amount = self._convert_to_report_currency(amount, currency, company, date_order)

            session_totals[session.id, method.id] += amount
            method_totals[method.id] += amount

            sessions[session.id] = session
            methods[method.id] = method

        session_lines = [
            {
                'record_id': f'{method_id}_{session_id}',
                'name': f'{methods[method_id].name} ({sessions[session_id].name})',
                'foldability': 'static',
                'style': 'normal',
                'amount_total': self._get_currency().round(amount),
            }
            for (session_id, method_id), amount in session_totals.items()
        ]

        method_lines = [
            {
                'record_id': method_id,
                'name': methods[method_id].name,
                'foldability': 'static',
                'style': 'bold',
                'amount_total': self._get_currency().round(amount),
            }
            for method_id, amount in method_totals.items()
        ]

        return session_lines + method_lines

    @report_section(id='discounts', name='Discounts', sequence=40)
    def _section_discounts(self):
        lines = self.env['pos.order.line'].search(self._get_sale_line_domain()).filtered(
            lambda line: line._has_discount(),
        )

        discount_amount = sum(
            self._convert_to_report_currency(
                line._get_discount_amount_for_report(),
                line.currency_id,
                line.company_id,
                line.order_id.date_order,
            )
            for line in lines
        )

        return {
            'name': _('Discounts'),
            'foldability': 'static',
            'style': 'bold',
            'count': len(lines),
            'amount': self._get_currency().round(discount_amount),
        }

    @report_section(id='invoices', name='Invoices', sequence=45)
    def _section_invoices(self):
        domain = self._get_order_domain() & Domain([('account_move', '!=', False)])
        orders = self.env['pos.order'].search_fetch(
            domain, ['is_singly_invoiced', 'is_globally_invoiced', 'account_move', 'session_id', 'company_id', 'date_order'],
        ).filtered(lambda order: order.is_singly_invoiced or order.is_globally_invoiced)

        if not orders:
            return {
                'name': _('Invoices'),
                'foldability': 'static',
                'style': 'bold',
                'count': 0,
                'amount_total': 0.0,
            }

        moves = orders.mapped('account_move')

        total = 0.0
        for move in moves:
            company = move.company_id
            total += self._convert_to_report_currency(move.amount_total_signed, company.currency_id, company, move.date)

        return {
            'name': _('Invoices'),
            'foldability': 'collapsed' if moves else 'static',
            'style': 'bold',
            'count': len(moves),
            'amount_total': self._get_currency().round(total),
        }

    @report_section(id='invoice_session', parent='invoices')
    def _section_invoices_sessions(self):
        domain = self._get_order_domain() & Domain([('account_move', '!=', False)])
        orders = self.env['pos.order'].search_fetch(
            domain, ['is_singly_invoiced', 'is_globally_invoiced', 'account_move', 'session_id'],
        ).filtered(lambda order: order.is_singly_invoiced or order.is_globally_invoiced)

        if not orders:
            return []

        sessions = defaultdict(set)
        for order in orders:
            sessions[order.session_id].add(order.account_move)

        return [
            {
                'record_id': session.id,
                'name': session.name,
                'foldability': 'collapsed',
                'style': 'bold',
                'count': len(moves),
                'amount_total': self._get_currency().round(sum(
                    self._convert_to_report_currency(
                        move.amount_total_signed,
                        move.company_id.currency_id,
                        move.company_id,
                        move.date,
                    )
                    for move in moves
                )),
            }
            for session, moves in sessions.items()
        ]

    @report_section(id='invoice_line', parent='invoice_session')
    def _section_invoices_lines(self):
        session_id = self.env.context.get('record_id')
        domain = self._get_order_domain() & Domain([('account_move', '!=', False), ('session_id', '=', session_id)])
        orders = self.env['pos.order'].search_fetch(
            domain, ['is_singly_invoiced', 'is_globally_invoiced', 'pos_reference', 'account_move'],
        ).filtered(lambda order: order.is_singly_invoiced or order.is_globally_invoiced)

        if not orders:
            return []

        moves = defaultdict(list)
        for order in orders:
            moves[order.account_move].append(order)

        return [
            {
                'record_id': move.id,
                'name': move.name,
                'foldability': 'static',
                'style': 'normal',
                'count': 1,
                'amount_total': self._get_currency().round(
                    self._convert_to_report_currency(
                        move.amount_total_signed,
                        move.company_id.currency_id,
                        move.company_id,
                        move.date,
                    ),
                ),
                'order_ref': ', '.join(order.pos_reference for order in move_orders if order.pos_reference),
            }
            for move, move_orders in moves.items()
        ]

    @report_section(id='session_control', name='Session Control', sequence=50)
    def _section_session_control(self):
        currency = self._get_currency()

        results = self.env['pos.order']._read_group(
            self._get_order_domain(),
            ['currency_id', 'company_id', 'date_order:day'],
            ['amount_paid:sum', 'amount_total:sum'],
        )

        expected = 0.0
        counted = 0.0
        for order_currency, company, date_order, paid, total in results:
            expected += self._convert_to_report_currency(total, order_currency, company, date_order)
            counted += self._convert_to_report_currency(paid, order_currency, company, date_order)

        return {
            'name': _('Session Control'),
            'foldability': 'collapsed',
            'style': 'bold',
            'expected': currency.round(expected),
            'counted': currency.round(counted),
            'difference': currency.round(counted - expected),
        }

    @report_section(id='sc_method', parent='session_control')
    def _section_session_control_payments(self):
        report_currency = self._get_currency()
        convert = self._convert_to_report_currency

        payment_groups = self.env['pos.payment']._read_group(
            [('pos_order_id', 'any', self._get_order_domain())],
            ['session_id', 'payment_method_id', 'currency_id', 'company_id', 'pos_order_id.date_order:day'],
            ['amount:sum'],
        )
        if not payment_groups:
            return []

        session_by_id = {}
        method_by_id = {}
        cash_keys = set()
        noncash_keys = set()
        expected = defaultdict(float)
        for session, method, currency, company, date_order, amount in payment_groups:
            session_id = session.id
            method_id = method.id
            key = (session_id, method_id)

            session_by_id[session_id] = session
            method_by_id[method_id] = method
            expected[key] += convert(amount, currency, company, date_order)

            if method.type == 'cash':
                cash_keys.add(key)
            else:
                noncash_keys.add(key)

        if not expected:
            return []

        sessions = self.env['pos.session'].browse(session_by_id.keys())
        sessions.fetch(['name', 'start_at', 'currency_id', 'company_id', 'opening_balance', 'closing_balance', 'correction_move_ids'])
        methods = self.env['pos.payment.method'].browse(method_by_id.keys())
        methods.fetch(['name', 'type', 'journal_id'])

        correction_moves = sessions.mapped('correction_move_ids')
        correction_moves.fetch(['amount_total', 'currency_id', 'company_id', 'date'])

        correction_by_session = {
            session.id: session.correction_move_ids
            for session in sessions if session.correction_move_ids
        }

        account_payment_keys = {
            key for key in noncash_keys
            if key[0] not in correction_by_session
        }

        counted = defaultdict(float)
        has_account_pay = set()
        if account_payment_keys:
            account_session_ids, account_method_ids = map(set, zip(*account_payment_keys))
            account_groups = self.env['account.payment'].sudo()._read_group(
                [
                    ('pos_session_id', 'in', list(account_session_ids)),
                    ('pos_payment_method_id', 'in', list(account_method_ids)),
                ],
                ['pos_session_id', 'pos_payment_method_id', 'payment_type', 'currency_id', 'company_id', 'date:day'],
                ['amount:sum'],
            )

            for session, method, payment_type, currency, company, pay_date, amount in account_groups:
                key = (session.id, method.id)
                if key not in account_payment_keys:
                    continue

                has_account_pay.add(key)
                signed_amount = -amount if payment_type == 'outbound' else amount
                counted[key] += convert(signed_amount, currency, company, pay_date)

        loss_accounts = methods.journal_id.loss_account_id
        loss_pairs = set()
        if correction_moves and loss_accounts:
            loss_groups = self.env['account.move.line']._read_group(
                [('move_id', 'in', correction_moves.ids), ('account_id', 'in', loss_accounts.ids)],
                ['move_id', 'account_id'],
            )
            loss_pairs = {(move.id, account.id) for move, account in loss_groups}

        result = []
        for (session_id, method_id), raw_expected in expected.items():
            session = session_by_id[session_id]
            method = method_by_id[method_id]
            key = (session_id, method_id)

            counted_amount = difference = 0.0
            has_moves = False

            if key in cash_keys:
                opening = convert(session.opening_balance, session.currency_id, session.company_id, session.start_at)
                counted_amount = convert(session.closing_balance, session.currency_id, session.company_id, session.start_at)
                difference = counted_amount - (raw_expected + opening)
                has_moves = True

            elif correction := correction_by_session.get(session_id):
                loss_account = method.journal_id.loss_account_id
                is_loss = bool(loss_account and (correction.id, loss_account.id) in loss_pairs)
                move_amount = convert(correction.amount_total, correction.currency_id, correction.company_id, correction.date)
                difference = -move_amount if is_loss else move_amount
                counted_amount = raw_expected + difference
                has_moves = True

            elif key in has_account_pay:
                counted_amount = counted[key]
                difference = counted_amount - raw_expected
                has_moves = True

            result.append({
                'record_id': f'{session_id}_{method_id}',
                'name': f'{method.name} ({session.name})',
                'foldability': 'collapsed' if has_moves else 'static',
                'style': 'normal',
                'expected': report_currency.round(raw_expected),
                'counted': report_currency.round(counted_amount),
                'difference': report_currency.round(difference),
            })

        return result

    @report_section(id='sc_move', parent='sc_method')
    def _section_session_control_cash_moves(self):
        record_id = self.env.context.get('record_id')
        if not record_id:
            return []

        session_id, method_id = map(int, record_id.split('_', 1))
        session = self.env['pos.session'].browse(session_id)
        method = self.env['pos.payment.method'].browse(method_id)

        if not session.exists() or not method.exists():
            return []

        return (
            self._build_cash_moves_cash(session, method)
            if method.type == 'cash'
            else self._build_cash_moves_non_cash(session, method)
        )

    def _build_cash_moves_cash(self, session, method):
        currency = self._get_currency()
        result = []
        if session.opening_balance > 0:
            result.append({
                'record_id': 'opening',
                'name': _('Cash Opening'),
                'foldability': 'static',
                'style': 'normal',
                'amount_total': currency.round(self._convert_to_report_currency(
                    session.opening_balance,
                    session.currency_id,
                    session.company_id,
                    session.start_at,
                )),
            })

        cash_moves = self.env['account.bank.statement.line'].search([
            ('pos_session_id', '=', session.id),
            ('move_id.journal_id', '=', method.journal_id.id),
        ])

        for counter, move in enumerate(cash_moves, 1):
            result.append({
                'record_id': move.id,
                'name': move.payment_ref or f'Cash {"in" if move.amount > 0 else "out"} {counter}',
                'foldability': 'static',
                'style': 'normal',
                'amount_total': currency.round(self._convert_to_report_currency(
                    move.amount,
                    move.currency_id,
                    move.company_id,
                    move.date,
                )),
            })

        return result

    def _build_cash_moves_non_cash(self, session, method):
        currency = self._get_currency()
        account_payments = self.env['account.payment'].search_fetch(
            [('pos_session_id', '=', session.id), ('pos_payment_method_id', '=', method.id)],
            ['amount_signed', 'currency_id', 'company_id', 'date'],
        )

        if account_payments:
            counted = sum(
                self._convert_to_report_currency(
                    payment.amount_signed,
                    payment.currency_id,
                    payment.company_id,
                    payment.date,
                )
                for payment in account_payments
            )

            pos_payments = self.env['pos.payment'].search_fetch(
                [('session_id', '=', session.id), ('payment_method_id', '=', method.id)],
                ['amount', 'pos_order_id'],
            )
            pos_payments.mapped('pos_order_id').fetch(['currency_id', 'company_id', 'date_order'])

            expected = sum(
                self._convert_to_report_currency(
                    payment.amount,
                    payment.pos_order_id.currency_id,
                    payment.pos_order_id.company_id,
                    payment.pos_order_id.date_order,
                )
                for payment in pos_payments
            )

            difference = counted - expected
            if currency.is_zero(difference):
                return []

            label = 'Profit' if difference > 0 else 'Loss'
        else:
            move = self.env['account.move'].search_fetch(
                [('ref', '=', _('Closing difference in %s (%s)', method.name, session.name))],
                ['amount_total', 'currency_id', 'company_id', 'date', 'line_ids'],
                limit=1,
            )
            if not move:
                return []

            is_loss = method.journal_id.loss_account_id in move.line_ids.account_id
            amount = self._convert_to_report_currency(
                move.amount_total,
                move.currency_id,
                move.company_id,
                move.date,
            )
            difference = -amount if is_loss else amount
            expected = 0.0
            counted = difference
            label = 'Loss' if is_loss else 'Profit'

        return [{
            'name': _('Difference observed during the counting (%s)', label),
            'foldability': 'static',
            'style': 'normal',
            'expected': currency.round(expected),
            'counted': currency.round(counted),
            'difference': currency.round(difference),
        }]

    @report_section(id='opening_notes', name='Opening Notes', sequence=60)
    def _section_opening_notes(self):
        if not self.is_session_report():
            return None

        session = self.env['pos.session'].browse(self.env.context.get('session_id'))
        return {
            'name': _('Opening Notes'),
            'foldability': 'static',
            'style': 'normal',
            'note': session.opening_notes or '' if session.exists() else '',
        }

    @report_section(id='closing_notes', name='Closing Notes', sequence=70)
    def _section_closing_notes(self):
        if not self.is_session_report():
            return None

        session = self.env['pos.session'].browse(self.env.context.get('session_id'))
        return {
            'name': _('Closing Notes'),
            'foldability': 'static',
            'style': 'normal',
            'note': session.closing_notes or '' if session.exists() else '',
        }

    def is_session_report(self):
        return bool(self.env.context.get('session_id'))

    def _get_sale_line_domain(self, is_refund=None):
        domain = Domain([('order_id.state', 'in', ['paid', 'done'])])

        if is_refund is not None:
            domain &= Domain([('order_id.is_refund', '=', is_refund)])

        if session_id := self.env.context.get('session_id'):
            domain &= Domain([('order_id.session_id', '=', session_id)])
        else:
            if date_from := self.env.context.get('date_from'):
                domain &= Domain([('order_id.date_order', '>=', date_from)])

            if date_to := self.env.context.get('date_to'):
                domain &= Domain([('order_id.date_order', '<=', date_to)])

            if config_ids := self.env.context.get('config_ids'):
                domain &= Domain([('order_id.config_id', 'in', config_ids)])

        return domain

    def _get_order_domain(self, states=('paid', 'done')):
        """Domain selecting the orders in scope."""
        domain = Domain([('state', 'in', states)])

        if session_id := self.env.context.get('session_id'):
            domain &= Domain([('session_id', '=', session_id)])
        else:
            if date_from := self.env.context.get('date_from'):
                domain &= Domain([('date_order', '>=', date_from)])

            if date_to := self.env.context.get('date_to'):
                domain &= Domain([('date_order', '<=', date_to)])

            if config_ids := self.env.context.get('config_ids'):
                domain &= Domain([('config_id', 'in', config_ids)])

        return domain

    def _is_discount_product(self, line):
        return line.order_id.config_id.module_pos_discount and line.product_id.id == line.order_id.config_id.discount_product_id.id

    def _convert_to_report_currency(self, amount, from_currency, company=False, date=False):
        """Convert amount from from_currency to the report currency."""
        to_currency = self._get_currency()

        if isinstance(from_currency, int):
            from_currency = self.env['res.currency'].browse(from_currency)
        if isinstance(company, int):
            company = self.env['res.company'].browse(company)

        if not from_currency or from_currency == to_currency:
            return amount

        return from_currency._convert(amount, to_currency, company, date)
