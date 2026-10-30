from collections import defaultdict
from functools import partial

from odoo import _, api, models
from odoo.fields import Domain
from odoo.tools import SQL, format_datetime

from .pos_report_handler import report_section


class PosSalesDetailReport(models.AbstractModel):
    _name = 'pos.sales.detail.report'
    _inherit = 'pos.report.handler'
    _description = 'POS Sales Detail Report Handler'

    def _get_filters(self):
        return [
            {'type': 'date_range', 'key': 'date_range', 'default': 'month'},
            {'type': 'multi_select', 'key': 'config_ids', 'model': 'pos.config', 'label': _('Point of Sale')},
            {
                'type': 'single_select',
                'key': 'session_id',
                'model': 'pos.session',
                'label': _('Session'),
                'domain': [('config_id', 'in', 'config_ids')],
            },
        ]

    def _get_filter_descriptions(self, options):
        descriptions = super()._get_filter_descriptions(options)

        config_ids = options.get('config_ids', [])
        if config_ids:
            configs = self.env['pos.config'].browse(config_ids)
            descriptions.append({
                'label': _('Points of Sale'),
                'value': ', '.join(configs.mapped('name')),
            })

        session_id = options.get('session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            descriptions.append({
                'label': _('Session'),
                'value': session.name,
            })

        return descriptions

    def _get_report_name(self, options):
        session = self.env['pos.session'].browse(options.get('session_id'))
        if not session.exists():
            return super()._get_report_name(options)
        return _('Daily Sales Report %s', 'Z' if session.state == 'closed' else 'X')

    def _get_pdf_templates(self):
        templates = super()._get_pdf_templates()
        for key, xml_id in [
            ('header', 'point_of_sale.pos_sales_detail_pdf_header'),
            ('data_row', 'point_of_sale.pos_sales_detail_pdf_data_row'),
        ]:
            if self.env.ref(xml_id, raise_if_not_found=False):
                templates[key] = xml_id
        return templates

    def _get_export_context(self, report, options, export_context):
        session = self.env['pos.session'].browse(options.get('session_id')).exists()
        if session:
            date_start, date_stop, configs = session.start_at, session.stop_at, session.config_id
        else:
            date_start, date_stop = options.get('date_from'), options.get('date_to')
            if config_ids := options.get('config_ids'):
                configs = self.env['pos.config'].browse(config_ids).exists()
            else:
                configs = self.env['pos.order'].search(self._get_order_domain(options)).config_id

        export_context.update({
            'session_name': session.name if session else False,
            'session_state': session.state if session else 'multiple',
            'config_names': configs.mapped('name') if not session else False,
            **{
                key: format_datetime(self.env, date, tz=self.env.context.get('tz')) if date else False
                for key, date in [('date_start', date_start), ('date_stop', date_stop)]
            },
        })
        return super()._get_export_context(report, options, export_context)

    _xlsx_product_columns = [
        {'id': 'discount', 'label': 'Disc', 'type': 'string'},
        {'id': 'combo_label', 'label': 'Combo', 'type': 'string'},
    ]

    def _get_xlsx_section_columns(self, section):
        columns = super()._get_xlsx_section_columns(section)
        if section.get('section_id') in ('sales', 'refunds'):
            return self._xlsx_product_columns + columns
        return columns

    def _get_xlsx_row_value(self, line, column):
        value = super()._get_xlsx_row_value(line, column)
        if column.get('id') == 'discount':
            return f"{value}%" if value else None
        return value

    def _get_sections_columns(self):
        quantity_digits = self.env['decimal.precision'].precision_get('Product Unit')
        return {
            'sales': [
                {'id': 'qty', 'label': _('Qty'), 'type': 'quantity', 'align': 'right', 'digits': quantity_digits},
                {'id': 'amount_total', 'label': _('Total'), 'type': 'monetary', 'align': 'right'},
            ],
            'refunds': [
                {'id': 'qty', 'label': _('Qty'), 'type': 'quantity', 'align': 'right', 'digits': quantity_digits},
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
            category = self._get_product_category(line.product_id)
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

    def _get_receipt_payments(self, options, orders):
        currency = self._get_currency(options)
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
    def get_sale_details_receipt_data(self, options):
        session = self.env['pos.session'].browse(options.get('session_id'))
        orders = self.env['pos.order'].search(self._get_order_domain(options))
        cancelled_orders = self.env['pos.order'].search(self._get_order_domain(options, states=('cancel',)))

        lines = orders.lines.filtered(lambda line: not self._is_discount_product(line))
        refund_lines = lines.filtered(lambda line: line.order_id.is_refund_or_negative())
        sold_lines = lines - refund_lines

        total_paid = sum(order.amount_total for order in orders)

        return {
            'products': self._get_receipt_products(sold_lines),
            'refund_products': self._get_receipt_products(refund_lines),
            'cancelled_products': self._get_receipt_products(cancelled_orders.lines),
            'taxes': self._get_receipt_taxes(sold_lines),
            'payments': self._get_receipt_payments(options, orders),
            'currency': {'total_paid': self._get_currency(options).round(total_paid)},
            'session_state': session.state if session else 'multiple',
        }

    def _get_currency(self, options):
        """Report display currency, cached for the current transaction."""
        config_ids = tuple(sorted(options.get('config_ids') or ()))
        session_id = options.get('session_id')
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

    def _get_sale_lines_query(self, options, is_refund=None, extra_domain=None):
        domain = self._get_sale_line_domain(options, is_refund=is_refund)
        if extra_domain:
            domain &= Domain(extra_domain)

        return self.env['pos.order.line']._search(domain)

    def _get_sale_line_totals_query(self, options, is_refund=False, group_fields=[], extra_domain=None):
        """Build the query for sale line totals."""
        query = self._get_sale_lines_query(options, is_refund, extra_domain)

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
            # Refund subtotals can be stored as absolute amounts. Preserve the
            # discounted line's sign while using its computed tax-excluded amount.
            SQL(
                "COALESCE(SUM(CASE WHEN %s * %s * (100.0 - COALESCE(%s, 0.0)) < 0 "
                "THEN -ABS(%s) ELSE ABS(%s) END), 0.0)",
                line_table['price_unit'],
                line_table['qty'],
                line_table['discount'],
                line_table['price_subtotal'],
                line_table['price_subtotal'],
            ),
        ]

        return query, select, group_by

    def _get_sale_line_totals(self, options, is_refund=False, group_fields=[], extra_domain=None):
        """Get sale line totals grouped by the given field."""
        query, select, group_by = self._get_sale_line_totals_query(options, is_refund, group_fields, extra_domain)

        rows = self.env.execute_query(query.select(*select, *group_by))

        totals = defaultdict(lambda: [0.0, 0.0])
        for qty, amount, curr_id, comp_id, date_order, *group in rows:
            total = totals[group[0] if len(group) == 1 else tuple(group) if group else 'default']
            total[0] += qty
            total[1] += self._convert_to_report_currency(options, amount, curr_id, comp_id, date_order)
        return totals

    @report_section(id='sales', name='Sales', sequence=10, foldability="expanded")
    def _section_sales(self, options):
        qty, amount = self._get_sale_line_totals(options).get('default', [0.0, 0.0])

        return {
            'name': _('Sales'),
            'foldability': 'expanded' if (qty or amount) else 'static',
            'qty': qty,
            'amount_total': self._get_currency(options).round(amount),
        }

    @report_section(id='category', parent='sales')
    def _section_sales_categories(self, options):
        return self._build_category_lines(options, is_refund=False)

    @report_section(id='product', parent='category')
    def _section_sales_products(self, options):
        return self._build_product_lines(options, is_refund=False)

    @report_section(id='refunds', name='Refunds', sequence=15)
    def _section_refunds(self, options):
        qty, amount = self._get_sale_line_totals(options, is_refund=True).get('default', [0.0, 0.0])

        return {
            'name': _('Refunds'),
            'foldability': 'collapsed' if (qty or amount) else 'static',
            'qty': qty,
            'amount_total': self._get_currency(options).round(amount),
        }

    @report_section(id='refund_category', parent='refunds')
    def _section_refunds_categories(self, options):
        return self._build_category_lines(options, is_refund=True)

    @report_section(id='refund_product', parent='refund_category')
    def _section_refunds_products(self, options):
        return self._build_product_lines(options, is_refund=True)

    def _build_category_lines(self, options, is_refund):
        product_totals = self._get_sale_line_totals(options, is_refund=is_refund, group_fields=['product_id'])
        products = self.env['product.product'].browse(list(product_totals))

        names = {}
        totals = defaultdict(lambda: [0.0, 0.0])
        for product in products:
            category = self._get_product_category(product)
            names[category.id or 0] = category.name or _('Not Categorized')
            qty, amount = product_totals[product.id]
            totals[category.id or 0][0] += qty
            totals[category.id or 0][1] += amount

        return [
            {
                'record_id': cid,
                'name': names[cid],
                'foldability': 'collapsed',
                'qty': totals[cid][0],
                'amount_total': self._get_currency(options).round(totals[cid][1]),
            }
            for cid in sorted(names, key=lambda cid: str(names[cid] or ''))
        ]

    def _build_product_lines(self, options, is_refund):
        category_id = options.get('record_id')
        category_domain = [
            ('product_id.product_tmpl_id.pos_categ_ids', '=', False)
            if not category_id
            else ('product_id.product_tmpl_id.pos_categ_ids', 'in', [category_id]),
        ]
        totals = self._get_sale_line_totals(
            options,
            is_refund=is_refund,
            group_fields=['product_id', 'price_unit', 'discount'],
            extra_domain=category_domain,
        )

        products = self.env['product.product'].browse({key[0] for key in totals})
        products = products.filtered(lambda product: self._get_product_category(product).id == (category_id or False))
        product_ids = set(products.ids)
        combo_lines = self.env['pos.order.line'].search(
            self._get_sale_line_domain(options, is_refund=is_refund)
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
            if product_id not in product_ids:
                continue
            product = products.browse(product_id)
            result.append({
                'record_id': f'{product_id}_{price}_{discount}'.replace('.', '_'),
                'name': product.display_name,
                'foldability': 'static',
                'qty': qty,
                'amount_total': self._get_currency(options).round(amount),
                'discount': discount,
                'uom': product.uom_id.name if product.uom_id != self.env.ref('uom.product_uom_unit') else False,
                'barcode': product.barcode or False,
                'combo_label': combo_labels.get((product_id, price, discount), ''),
            })

        return sorted(result, key=lambda line: line['name'])

    def _get_tax_totals(self, options, is_refund=False):
        """Aggregate tax base and tax amount from POS order lines."""
        query = self._get_sale_lines_query(options, is_refund)

        line_table = query.table
        order_table = line_table._join('order_id')
        config_table = order_table._join('config_id')

        group_by = [
            config_table['currency_id'],
            line_table['company_id'],
            SQL("CAST(%s AS date)", order_table['date_order']),
        ]
        query.groupby = SQL(", ").join(group_by)

        amount_sign = SQL("1")
        if is_refund:
            amount_sign = SQL(
                "(CASE WHEN %s * %s * (100.0 - COALESCE(%s, 0.0)) < 0 THEN -1 ELSE 1 END) "
                "* (CASE WHEN %s < 0 THEN -1 ELSE 1 END)",
                line_table['price_unit'], line_table['qty'], line_table['discount'],
                line_table['price_subtotal'],
            )
        select = [
            SQL("COALESCE(SUM(%s * %s), 0.0)", line_table['price_subtotal'], amount_sign),
            SQL("COALESCE(SUM(%s * %s), 0.0)", line_table['price_subtotal_incl'], amount_sign),
        ]

        rows = self.env.execute_query(query.select(*select, *group_by))

        base = 0.0
        tax = 0.0
        for subtotal, subtotal_incl, currency_id, company_id, date_order in rows:
            base += self._convert_to_report_currency(options, subtotal, currency_id, company_id, date_order)
            tax += self._convert_to_report_currency(options, subtotal_incl - subtotal, currency_id, company_id, date_order)

        return base, tax

    @report_section(id='taxes_sales', name='Taxes on Sales', sequence=20)
    def _section_taxes_sales(self, options):
        base, tax = self._get_tax_totals(options)
        return {
            'name': _('Taxes on Sales'),
            'foldability': 'collapsed',
            'tax_amount': tax,
            'base_amount': base,
            'amount_total': base + tax,
        }

    @report_section(id='tax_line', parent='taxes_sales')
    def _section_taxes_sales_lines(self, options):
        return self._build_tax_lines(options, is_refund=False)

    @report_section(id='taxes_refunds', name='Taxes on Refunds', sequence=25)
    def _section_taxes_refunds(self, options):
        base, tax = self._get_tax_totals(options, is_refund=True)
        return {
            'name': _('Taxes on Refunds'),
            'foldability': 'collapsed',
            'tax_amount': tax,
            'base_amount': base,
            'amount_total': base + tax,
        }

    @report_section(id='refund_tax_line', parent='taxes_refunds')
    def _section_taxes_refunds_lines(self, options):
        return self._build_tax_lines(options, is_refund=True)

    def _build_tax_lines(self, options, is_refund):
        domain = self._get_sale_line_domain(options, is_refund=is_refund)
        lines = self.env['pos.order.line'].search(domain)
        taxes = {}
        for line in lines:
            if self._is_discount_product(line):
                continue
            convert = partial(
                self._convert_to_report_currency, options,
                from_currency=line.currency_id,
                company=line.company_id,
                date=line.order_id.date_order,
            )
            if line.tax_ids_after_fiscal_position:
                computed = line.tax_ids_after_fiscal_position.sudo().compute_all(
                    line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                    line.currency_id, line.qty if is_refund else abs(line.qty), product=line.product_id,
                    partner=line.order_id.partner_id or False,
                )
                for tax in computed['taxes']:
                    taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0})
                    taxes[tax['id']]['tax_amount'] += convert(tax['amount'])
                    taxes[tax['id']]['base_amount'] += convert(line.currency_id.round(tax['base']))
            else:
                taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0})
                amount = line.price_subtotal_incl
                if is_refund:
                    price = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
                    amount = -abs(amount) if price < 0 else abs(amount)
                taxes[0]['base_amount'] += convert(amount)
        return [
            {
                'record_id': tid,
                'name': t['name'],
                'foldability': 'static',
                'tax_amount': t['tax_amount'],
                'base_amount': t['base_amount'],
                'amount_total': t['base_amount'] + t['tax_amount'],
            }
            for tid, t in taxes.items()
        ]

    @report_section(id='payments', name='Payments', sequence=30)
    def _section_payments(self, options):
        payment_groups = self.env['pos.payment']._read_group(
            [('pos_order_id', 'any', self._get_order_domain(options))],
            ['pos_order_id.currency_id', 'pos_order_id.company_id', 'pos_order_id.date_order:day'],
            ['amount:sum'],
        )

        total = 0.0
        for currency, company, date_order, amount in payment_groups:
            total += self._convert_to_report_currency(options, amount, currency, company, date_order)

        return {
            'name': _('Payments'),
            'foldability': 'collapsed' if payment_groups else 'static',
            'amount_total': self._get_currency(options).round(total),
        }

    def _get_payment_totals_by(self, options, group_field, extra_domain=()):
        groups = self.env['pos.payment']._read_group(
            [('pos_order_id', 'any', self._get_order_domain(options)), *extra_domain],
            [group_field, 'pos_order_id.currency_id', 'pos_order_id.company_id', 'pos_order_id.date_order:day'],
            ['amount:sum'],
        )
        totals = defaultdict(float)
        for record, currency, company, date_order, amount in groups:
            totals[record] += self._convert_to_report_currency(options, amount, currency, company, date_order)
        return totals

    @report_section(id='payment_method', parent='payments')
    def _section_payments_methods(self, options):
        return [
            {
                'record_id': method.id,
                'name': method.name,
                'foldability': 'collapsed',
                'amount_total': self._get_currency(options).round(amount),
            }
            for method, amount in self._get_payment_totals_by(options, 'payment_method_id').items()
        ]

    @report_section(id='payment_method_session', parent='payment_method')
    def _section_payments_method_sessions(self, options):
        method_id = options.get('record_id')
        if not method_id:
            return []

        method = self.env['pos.payment.method'].browse(method_id)
        totals = self._get_payment_totals_by(options, 'session_id', [('payment_method_id', '=', method_id)])
        return [
            {
                'record_id': f'{method_id}_{session.id}',
                'name': f'{method.name} ({session.name})',
                'foldability': 'static',
                'amount_total': self._get_currency(options).round(amount),
            }
            for session, amount in totals.items()
        ]

    @report_section(id='discounts', name='Discounts', sequence=40)
    def _section_discounts(self, options):
        lines = self.env['pos.order.line'].search(self._get_sale_line_domain(options)).filtered(
            lambda line: line._has_discount(),
        )

        discount_amount = sum(
            self._convert_to_report_currency(
                options,
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
            'count': len(lines),
            'amount': self._get_currency(options).round(discount_amount),
        }

    @report_section(id='invoices', name='Invoices', sequence=45)
    def _section_invoices(self, options):
        domain = self._get_order_domain(options) & Domain([('account_move', '!=', False)])
        orders = self.env['pos.order'].search_fetch(
            domain, ['is_singly_invoiced', 'account_move', 'session_id', 'company_id', 'date_order'],
        ).filtered('is_singly_invoiced')

        if not orders:
            return {
                'name': _('Invoices'),
                'foldability': 'static',
                'count': 0,
                'amount_total': 0.0,
            }

        moves = orders.mapped('account_move')

        total = 0.0
        for move in moves:
            company = move.company_id
            total += self._convert_to_report_currency(options, move.amount_total_signed, company.currency_id, company, move.date)

        return {
            'name': _('Invoices'),
            'foldability': 'collapsed' if moves else 'static',
            'count': len(moves),
            'amount_total': self._get_currency(options).round(total),
        }

    @report_section(id='invoice_session', parent='invoices')
    def _section_invoices_sessions(self, options):
        domain = self._get_order_domain(options) & Domain([('account_move', '!=', False)])
        orders = self.env['pos.order'].search_fetch(
            domain, ['is_singly_invoiced', 'account_move', 'session_id'],
        ).filtered('is_singly_invoiced')

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
                'count': len(moves),
                'amount_total': self._get_currency(options).round(sum(
                    self._convert_to_report_currency(
                        options,
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
    def _section_invoices_lines(self, options):
        session_id = options.get('record_id')
        domain = self._get_order_domain(options) & Domain([('account_move', '!=', False), ('session_id', '=', session_id)])
        orders = self.env['pos.order'].search_fetch(
            domain, ['is_singly_invoiced', 'pos_reference', 'account_move'],
        ).filtered('is_singly_invoiced')

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
                'count': 1,
                'amount_total': self._get_currency(options).round(
                    self._convert_to_report_currency(
                        options,
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
    def _section_session_control(self, options):
        currency = self._get_currency(options)
        lines = self._section_session_control_payments(options)
        return {
            'name': _('Session Control'),
            'foldability': 'collapsed',
            **{
                column: currency.round(sum(line[column] for line in lines))
                for column in ('expected', 'counted', 'difference')
            },
        }

    @report_section(id='sc_method', parent='session_control')
    def _section_session_control_payments(self, options):
        report_currency = self._get_currency(options)
        order_domain = self._get_order_domain(options)
        convert = partial(self._convert_to_report_currency, options)

        payment_groups = self.env['pos.payment']._read_group(
            [('pos_order_id', 'any', order_domain)],
            ['session_id', 'payment_method_id', 'currency_id', 'company_id', 'pos_order_id.date_order:day'],
            ['amount:sum'],
        )
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

        if session_id := options.get('session_id'):
            sessions_in_scope = self.env['pos.session'].browse(session_id).exists()
        else:
            sessions_in_scope = self.env['pos.order'].search(order_domain).session_id

        # A session still has cash to reconcile when no orders were paid in cash.
        for session in self.env['pos.session'].browse(session_by_id) | sessions_in_scope:
            if cash_method := session.config_id._get_cash_payment_method():
                key = (session.id, cash_method.id)
                expected.setdefault(key, 0.0)
                cash_keys.add(key)
                session_by_id[session.id] = session
                method_by_id[cash_method.id] = cash_method

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
            correction = correction_by_session.get(session_id, self.env['account.move']).filtered(
                lambda move: move.journal_id == method.journal_id,
            )

            if key in cash_keys:
                opening = convert(session.opening_balance, session.currency_id, session.company_id, session.start_at)
                counted_amount = convert(session.closing_balance, session.currency_id, session.company_id, session.start_at)
                difference = counted_amount - (raw_expected + opening)
                has_moves = True

            elif correction:
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
                'expected': report_currency.round(raw_expected),
                'counted': report_currency.round(counted_amount),
                'difference': report_currency.round(difference),
            })

        return result

    @report_section(id='sc_move', parent='sc_method')
    def _section_session_control_cash_moves(self, options):
        record_id = options.get('record_id')
        if not record_id:
            return []

        session_id, method_id = map(int, record_id.split('_', 1))
        session = self.env['pos.session'].browse(session_id)
        method = self.env['pos.payment.method'].browse(method_id)

        if not session.exists() or not method.exists():
            return []

        return (
            self._build_cash_moves_cash(options, session, method)
            if method.type == 'cash'
            else self._build_cash_moves_non_cash(options, session, method)
        )

    def _build_cash_moves_cash(self, options, session, method):
        currency = self._get_currency(options)
        result = []
        if session.opening_balance > 0:
            result.append({
                'record_id': 'opening',
                'name': _('Cash Opening'),
                'foldability': 'static',
                'expected': currency.round(self._convert_to_report_currency(
                    options,
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
                'name': move.payment_ref or (
                    _('Cash in %s', counter) if move.amount > 0 else _('Cash out %s', counter)
                ),
                'foldability': 'static',
                'expected': currency.round(self._convert_to_report_currency(
                    options,
                    move.amount,
                    move.currency_id,
                    move.company_id,
                    move.date,
                )),
            })

        return result

    def _build_cash_moves_non_cash(self, options, session, method):
        currency = self._get_currency(options)
        account_payments = self.env['account.payment'].search_fetch(
            [('pos_session_id', '=', session.id), ('pos_payment_method_id', '=', method.id)],
            ['amount_signed', 'currency_id', 'company_id', 'date'],
        )

        if account_payments:
            counted = sum(
                self._convert_to_report_currency(
                    options,
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
                    options,
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

            label = _('Profit') if difference > 0 else _('Loss')
        else:
            move = session.correction_move_ids.filtered(lambda m: m.journal_id == method.journal_id)[:1]
            if not move:
                return []

            is_loss = method.journal_id.loss_account_id in move.line_ids.account_id
            amount = self._convert_to_report_currency(
                options,
                move.amount_total,
                move.currency_id,
                move.company_id,
                move.date,
            )
            difference = -amount if is_loss else amount
            expected = 0.0
            counted = difference
            label = _('Loss') if is_loss else _('Profit')

        return [{
            'name': _('Difference observed during the counting (%s)', label),
            'foldability': 'static',
            'expected': currency.round(expected),
            'counted': currency.round(counted),
            'difference': currency.round(difference),
        }]

    @report_section(id='opening_notes', name='Opening Notes', sequence=60)
    def _section_opening_notes(self, options):
        if not self.is_session_report(options):
            return None

        session = self.env['pos.session'].browse(options.get('session_id'))
        return {
            'name': _('Opening Notes'),
            'foldability': 'static',
            'note': session.opening_notes or '' if session.exists() else '',
        }

    @report_section(id='closing_notes', name='Closing Notes', sequence=70)
    def _section_closing_notes(self, options):
        if not self.is_session_report(options):
            return None

        session = self.env['pos.session'].browse(options.get('session_id'))
        return {
            'name': _('Closing Notes'),
            'foldability': 'static',
            'note': session.closing_notes or '' if session.exists() else '',
        }

    def is_session_report(self, options):
        return bool(options.get('session_id'))

    def _get_product_category(self, product):
        return product.product_tmpl_id.pos_categ_ids[:1]

    def _get_sale_line_domain(self, options, is_refund=None):
        domain = Domain([('order_id.state', 'in', ['paid', 'done'])])

        if is_refund is not None:
            refund_domain = Domain('order_id.is_refund', '=', True) | Domain('order_id.amount_total', '<', 0)
            domain &= refund_domain if is_refund else ~refund_domain

        if session_id := options.get('session_id'):
            domain &= Domain([('order_id.session_id', '=', session_id)])
        else:
            if date_from := options.get('date_from'):
                domain &= Domain([('order_id.date_order', '>=', date_from)])

            if date_to := options.get('date_to'):
                domain &= Domain([('order_id.date_order', '<=', date_to)])

            if config_ids := options.get('config_ids'):
                domain &= Domain([('order_id.config_id', 'in', config_ids)])

        return domain

    def _get_order_domain(self, options, states=('paid', 'done')):
        """Domain selecting the orders in scope."""
        domain = Domain([('state', 'in', states)])

        if session_id := options.get('session_id'):
            domain &= Domain([('session_id', '=', session_id)])
        else:
            if date_from := options.get('date_from'):
                domain &= Domain([('date_order', '>=', date_from)])

            if date_to := options.get('date_to'):
                domain &= Domain([('date_order', '<=', date_to)])

            if config_ids := options.get('config_ids'):
                domain &= Domain([('config_id', 'in', config_ids)])

        return domain

    def _is_discount_product(self, line):
        return False

    def _convert_to_report_currency(self, options, amount, from_currency, company=False, date=False):
        """Convert amount from from_currency to the report currency."""
        to_currency = self._get_currency(options)

        if isinstance(from_currency, int):
            from_currency = self.env['res.currency'].browse(from_currency)
        if isinstance(company, int):
            company = self.env['res.company'].browse(company)

        if not from_currency or from_currency == to_currency:
            return amount

        return from_currency._convert(amount, to_currency, company, date)
