# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from odoo.addons.point_of_sale.report.pos_report_handler import report_section
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestPosReportHandler(TransactionCase):

    @contextmanager
    def _handler_with_sections(self, *sections):
        handler = self.env['pos.report.handler']
        handler_class = self.env.registry['pos.report.handler']
        with ExitStack() as stack:
            # Keep real discovery without reading or populating the registry's
            # stable cache with temporary section methods.
            stack.enter_context(patch.object(
                handler_class, '_get_section_methods',
                handler_class._get_section_methods.__wrapped__,
            ))
            for method in sections:
                stack.enter_context(patch.object(handler_class, f'_test_{method.__name__}', method, create=True))
            yield handler

    def test_section_discovery_and_ordering(self):
        @report_section(id='first', sequence=10)
        def first_root_section(handler, options):
            return {'amount': 1}

        @report_section(id='last', sequence=20)
        def second_root_section(handler, options):
            return {'amount': 2}

        @report_section(id='child_first', parent='first', sequence=10)
        def first_child_section(handler, options):
            return {'amount': 3}

        @report_section(id='child_last', parent='first', sequence=20)
        def second_child_section(handler, options):
            return {'amount': 4}

        with self._handler_with_sections(second_root_section, second_child_section, first_root_section, first_child_section) as handler:
            self.assertEqual([line['section_id'] for line in handler._get_sections_data({})], ['first', 'last'])
            self.assertEqual(
                [line['section_id'] for line in handler._get_unfold_lines({}, 'first')],
                ['child_first', 'child_last'],
            )

    def test_line_normalization_and_empty_values(self):
        @report_section(id='summary', name='Summary', sequence=10)
        def summary(handler, options):
            return {
                'record_id': 7, 'section_id': 'ignored', 'name': 'Custom summary', 'sequence': 20,
                'foldability': 'static', 'lines': [{'amount': 99}], 'columns': ['amount'],
                'amount': 12, 'note': 'Paid',
            }

        @report_section(id='details')
        def details(handler, options):
            return [None, {}, {'amount': 0, 'note': '   ', 'missing': None}, {'amount': 5}]

        with self._handler_with_sections(summary, details) as handler:
            sections = handler._get_sections_data({})
            self.assertEqual(sections[0]['values'], {'amount': 5})
            self.assertEqual(sections[1], {
                'section_id': 'summary', 'record_id': 7, 'name': 'Custom summary',
                'sequence': 20, 'foldability': 'static', 'values': {'amount': 12, 'note': 'Paid'},
                'lines': [], 'columns': [],
            })

    def test_empty_section_with_children(self):
        @report_section(id='group')
        def group(handler, options):
            return {'name': 'Group'}

        @report_section(id='child', parent='group')
        def child(handler, options):
            return {'amount': 1}

        @report_section(id='empty')
        def empty(handler, options):
            return {'name': 'Empty', 'amount': 0}

        with self._handler_with_sections(group, child, empty) as handler:
            sections = handler._get_sections_data({})
            self.assertEqual([line['section_id'] for line in sections], ['group'])
            self.assertEqual(sections[0]['values'], {})

    def test_recursive_unfolding_and_parent_record(self):
        @report_section(id='expanded', parent='root', sequence=10, foldability='expanded')
        def expanded(handler, options):
            return {'record_id': 11, 'amount': options.get('record_id')}

        @report_section(id='collapsed', parent='root', sequence=20)
        def collapsed(handler, options):
            return {'record_id': 12, 'amount': options.get('record_id')}

        @report_section(id='expanded_leaf', parent='expanded', foldability='static')
        def expanded_leaf(handler, options):
            return {'amount': options.get('record_id')}

        @report_section(id='collapsed_leaf', parent='collapsed', foldability='static')
        def collapsed_leaf(handler, options):
            return {'amount': options.get('record_id')}

        for foldability in ('expanded', 'collapsed', 'static'):
            @report_section(id='root', foldability=foldability)
            def root(handler, options):
                return {'record_id': 7, 'amount': 1}

            for unfold_all in (False, True):
                with self.subTest(foldability=foldability, unfold_all=unfold_all):
                    with self._handler_with_sections(
                        root, expanded, collapsed, expanded_leaf, collapsed_leaf,
                    ) as handler:
                        section, = handler._get_sections_data({'unfold_all': unfold_all})
                        self.assertEqual(section['foldability'], foldability)
                        if foldability != 'expanded' and not unfold_all:
                            self.assertEqual(section['lines'], [])
                            continue
                        first, second = section['lines']
                        self.assertEqual([first['values'], second['values']], [{'amount': 7}, {'amount': 7}])
                        self.assertEqual(first['lines'][0]['values'], {'amount': 11})
                        self.assertEqual(first['lines'][0]['foldability'], 'static')
                        self.assertEqual(
                            [line['values'] for line in second['lines']],
                            [{'amount': 12}] if unfold_all else [],
                        )

    def test_invalid_section_definitions(self):
        @report_section(id='duplicate')
        def first(handler, options):
            return {'amount': 1}

        @report_section(id='duplicate')
        def second(handler, options):
            return {'amount': 2}

        @report_section(id='orphan', parent='missing')
        def orphan(handler, options):
            return {'amount': 3}

        with self.assertRaisesRegex(ValidationError, "Duplicate section ID 'duplicate'"):
            with self._handler_with_sections(first, second) as handler:
                handler._validate_sections()
        with self.assertRaisesRegex(ValidationError, "references parent 'missing' which does not exist"):
            with self._handler_with_sections(orphan) as handler:
                handler._validate_sections()

    def test_unfolding_passes_options_and_resets_parent_record(self):
        @report_section(id='root')
        def root(handler, options):
            return {'record_id': 7, 'amount': options['amount']}

        @report_section(id='child', parent='root')
        def child(handler, options):
            return {'amount': options['amount'] + options['record_id']}

        @report_section(id='leaf', parent='child')
        def leaf(handler, options):
            return {'parent': str(options.get('record_id')), 'amount': options['amount']}

        with self._handler_with_sections(root, child, leaf) as handler:
            section, = handler.with_context(record_id=99)._get_sections_data({'amount': 10, 'unfold_all': True})
        child, = section['lines']
        self.assertEqual(child['values']['amount'], 17)
        self.assertEqual(child['lines'][0]['values'], {'parent': 'None', 'amount': 10})


class TestPosReportCommon(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('point_of_sale.pos_sales_detail_report')
        cls.basic_config.open_ui()
        cls.session = cls.basic_config.current_session_id
        cls.session.set_opening_control(0, None)
        cls.category = cls.env['pos.category'].create({'name': 'Drinks'})
        cls.tax = cls.env['account.tax'].create({
            'name': 'Report VAT 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_excluded',
        })
        cls.coffee = cls.create_product('Report Coffee', cls.categ_basic, 100, tax_ids=cls.tax.ids)
        cls.coffee.pos_categ_ids = cls.category
        cls.tea = cls.create_product('Report Tea', cls.categ_basic, 50)
        cls._create_report_order([
            (cls.coffee, 2, 100, 10),
            (cls.coffee, 1, 100, 0),
            (cls.tea, 1, 50, 0),
        ])
        cls._create_report_order(
            [(cls.coffee, -1, 100, 0)], date='2026-01-11 10:00:00', is_refund=True,
        )
        # Large excluded orders make accidental inclusion visible in every total.
        for state in ('draft', 'cancel'):
            cls._create_report_order([(cls.coffee, 100, 100, 0)], state=state)

    @classmethod
    def _create_report_order(cls, lines, *, session=None, date='2026-01-10 10:00:00', state='paid', is_refund=False):
        session = session or cls.session
        commands = []
        total = tax = 0
        for product, qty, price, discount in lines:
            amounts = product.taxes_id.compute_all(
                price * (1 - discount / 100), session.currency_id, qty, product=product,
            )
            subtotal = amounts['total_excluded']
            subtotal_incl = amounts['total_included']
            total += subtotal_incl
            tax += subtotal_incl - subtotal
            commands.append(Command.create({
                'product_id': product.id,
                'qty': qty,
                'price_unit': price,
                'discount': discount,
                'tax_ids': [Command.set(product.taxes_id.ids)],
                'price_subtotal': subtotal,
                'price_subtotal_incl': subtotal_incl,
            }))
        order = cls.env['pos.order'].create({
            'session_id': session.id,
            'date_order': date,
            'state': state,
            'is_refund': is_refund,
            'lines': commands,
            'amount_total': total,
            'amount_tax': tax,
            'amount_paid': total if state in ('paid', 'done') else 0,
            'amount_return': 0,
        })
        if state in ('paid', 'done'):
            cls.env['pos.payment'].create({
                'pos_order_id': order.id,
                'payment_method_id': session.config_id.payment_method_ids.filtered(lambda pm: pm.type == 'bank')[:1].id,
                'amount': total,
            })
        return order

    def _report_sections(self, **options):
        return self.report.get_report_data(options)['sections']

    def _unfold(self, section_id, record_id=None):
        return self.report.get_unfold_data(
            {'session_id': self.session.id, 'record_id': record_id}, section_id,
        )['lines']


@tagged('post_install', '-at_install')
class TestPosReport(TestPosReportCommon):

    def test_sales_and_refund_totals(self):
        sections = {s['section_id']: s for s in self._report_sections(session_id=self.session.id)}
        self.assertEqual(sections['sales']['values'], {'qty': 4, 'amount_total': 330})
        self.assertEqual(sections['refunds']['values'], {'qty': 1, 'amount_total': -100})
        self.assertEqual(sections['taxes_sales']['values'], {'tax_amount': 28, 'base_amount': 330, 'amount_total': 358})
        self.assertEqual(sections['taxes_refunds']['values'], {'tax_amount': -10, 'base_amount': -100, 'amount_total': -110})
        self.assertEqual(sections['payments']['values'], {'amount_total': 248})
        self.assertEqual(sections['discounts']['values'], {'count': 1, 'amount': 22})
        self.assertEqual(sections['session_control']['values'], {'expected': 248, 'counted': 0, 'difference': 0})

    def test_product_grouping(self):
        categories = {line['record_id']: line['values'] for line in self._unfold('sales')}
        self.assertEqual(categories, {
            self.category.id: {'qty': 3, 'amount_total': 280},
            0: {'qty': 1, 'amount_total': 50},
        })
        products = self._unfold('category', self.category.id)
        # The same product at different discounts must remain in separate rows.
        self.assertEqual(sorted((p['values']['discount'], p['values']['qty'], p['values']['amount_total']) for p in products), [
            (0, 1, 100), (10, 2, 180),
        ])
        self.assertEqual([p['name'] for p in self._unfold('category', 0)], [self.tea.display_name])

    def test_tax_details(self):
        sales_taxes = {line['record_id']: line['values'] for line in self._unfold('taxes_sales')}
        self.assertEqual(sales_taxes, {
            self.tax.id: {'tax_amount': 28, 'base_amount': 280, 'amount_total': 308},
            0: {'tax_amount': 0, 'base_amount': 50, 'amount_total': 50},
        })
        refund_taxes = {line['record_id']: line['values'] for line in self._unfold('taxes_refunds')}
        self.assertEqual(refund_taxes, {
            self.tax.id: {'tax_amount': -10, 'base_amount': -100, 'amount_total': -110},
        })

    def test_payment_methods(self):
        sale = self.session.order_ids.filtered(lambda order: order.state == 'paid' and not order.is_refund)
        bank_payment = sale.payment_ids
        bank_method = bank_payment.payment_method_id
        # Split the sale payment while keeping the order total unchanged.
        bank_payment.amount -= 50
        self.env['pos.payment'].create({
            'pos_order_id': sale.id,
            'payment_method_id': self.cash_pm1.id,
            'amount': 50,
        })
        self.assertCountEqual(
            [(line['record_id'], line['foldability'], line['values']['amount_total'])
             for line in self._unfold('payments')],
            [(bank_method.id, 'collapsed', 198), (self.cash_pm1.id, 'collapsed', 50)],
        )
        self.assertEqual(
            [(line['record_id'], line['values']['amount_total'])
             for line in self._unfold('payment_method', bank_method.id)],
            [(f'{bank_method.id}_{self.session.id}', 198)],
        )

    def test_session_control_totals_match_payment_lines(self):
        sale = self.session.order_ids.filtered(lambda order: order.state == 'paid' and not order.is_refund)
        sale.payment_ids.amount -= 200
        self.env['pos.payment'].create({
            'pos_order_id': sale.id,
            'payment_method_id': self.cash_pm1.id,
            'amount': 200,
        })
        self.session.write({'opening_balance': 200, 'closing_balance': 100})

        sections = {section['section_id']: section for section in self._report_sections(session_id=self.session.id)}
        lines = {line['record_id']: line['values'] for line in self._unfold('session_control')}
        self.assertEqual(lines[f'{self.session.id}_{self.cash_pm1.id}'], {
            'expected': 200, 'counted': 100, 'difference': -300,
        })
        self.assertEqual(sections['session_control']['values'], {
            'expected': 248, 'counted': 100, 'difference': -300,
        })

    def test_report_filters(self):
        other_config = self.basic_config.copy({'name': 'Other report shop'})
        other_config.open_ui()
        other_session = other_config.current_session_id
        self._create_report_order([(self.tea, 1, 7, 0)], session=other_session)
        self._create_report_order([(self.tea, 1, 11, 0)], date='2026-01-10 09:59:59')
        self._create_report_order([(self.tea, 1, 13, 0)], date='2026-01-11 10:00:01')
        handler = self.env['pos.sales.detail.report']
        options = dict(
            date_from='2026-01-10 10:00:00', date_to='2026-01-11 10:00:00',
            config_ids=self.basic_config.ids,
        )
        sections = {s['section_id']: s['values'] for s in handler._get_sections_data(options)}
        # Both date bounds are inclusive, and the other shop is excluded.
        self.assertEqual(sections['sales'], {'qty': 4, 'amount_total': 330})
        self.assertEqual(sections['refunds'], {'qty': 1, 'amount_total': -100})
        self.assertEqual(sections['payments'], {'amount_total': 248})

        session_options = dict(
            options,
            session_id=other_session.id, date_from='2099-01-01 00:00:00',
        )
        sections = {s['section_id']: s['values'] for s in handler._get_sections_data(session_options)}
        self.assertEqual(sections['sales'], {'qty': 1, 'amount_total': 7})
        self.assertEqual(sections['payments'], {'amount_total': 7})

    def test_empty_report(self):
        options = dict(
            date_from='2099-01-01 00:00:00', date_to='2099-01-31 23:59:59', config_ids=self.basic_config.ids,
        )
        data = self.report.get_report_data(options)
        self.assertEqual(data['sections'], [])
        self.assertEqual(data['report_name'], self.report.name)
        export_context, = self.report._get_export_context(options)
        self.assertEqual(export_context['report_name'], self.report.name)

    def test_filter_dates_use_local_timezone(self):
        options = {
            'date_from': '2026-10-31 18:30:00',
            'date_to': '2026-11-30 18:29:59',
        }
        handler = self.report._get_handler().with_context(tz='Asia/Kolkata', lang='en_US')
        descriptions = handler._get_filter_descriptions(options)
        self.assertEqual([description['value'] for description in descriptions], [
            '11/01/2026 12:00:00 AM', '11/30/2026 11:59:59 PM',
        ])

    def test_explicit_options_ignore_report_filters_in_context(self):
        options = {'session_id': self.session.id}
        report = self.report.with_context(session_id=-1, record_id=-1, unfold_all=True)
        data = report.get_report_data(options)
        self.assertEqual(data['report_name'], 'Daily Sales Report X')
        sales = next(section for section in data['sections'] if section['section_id'] == 'sales')
        self.assertEqual(sales['values']['amount_total'], 330)
        products = report.get_unfold_data({**options, 'record_id': 0}, 'category')['lines']
        self.assertEqual([line['name'] for line in products], [self.tea.display_name])
        export_context, = report._get_export_context(options)
        self.assertEqual(export_context['filters'], [{'label': 'Session', 'value': self.session.name}])
        self.assertEqual(options, {'session_id': self.session.id})

    def test_session_notes(self):
        self.session.write({
            'opening_notes': 'Opening float checked',
            'closing_notes': 'Closing balance checked',
        })
        sections = {s['section_id']: s for s in self._report_sections(session_id=self.session.id)}
        self.assertEqual(sections['opening_notes']['values'], {'note': 'Opening float checked'})
        self.assertEqual(sections['closing_notes']['values'], {'note': 'Closing balance checked'})
        sections = {s['section_id'] for s in self._report_sections(config_ids=self.basic_config.ids)}
        self.assertTrue(sections.isdisjoint({'opening_notes', 'closing_notes'}))

    def test_currency_conversion(self):
        self.other_currency_config.open_ui()
        session = self.other_currency_config.current_session_id
        self.env['res.currency.rate'].create([
            {'name': '2026-01-01', 'currency_id': self.company_currency.id, 'company_id': self.company.id, 'rate': 1},
            {'name': '2026-01-01', 'currency_id': self.other_currency.id, 'company_id': self.company.id, 'rate': 0.5},
        ])
        self._create_report_order([(self.tea, 1, 10, 0)], session=session)
        handler = self.env['pos.sales.detail.report']
        self.assertEqual(handler._get_currency({'session_id': session.id}), self.other_currency)
        self.assertEqual(
            handler._get_currency({'config_ids': self.other_currency_config.ids}),
            self.other_currency,
        )
        options = dict(
            config_ids=(self.basic_config | self.other_currency_config).ids,
            date_from='2026-01-01 00:00:00', date_to='2026-01-31 23:59:59',
        )
        self.assertEqual(handler._get_currency(options), self.company_currency)
        sections = {s['section_id']: s['values'] for s in handler._get_sections_data(options)}
        self.assertEqual(sections['sales'], {'qty': 5, 'amount_total': 350})
        self.assertEqual(sections['payments'], {'amount_total': 268})

        self._create_report_order([(self.coffee, 1, 10, 0)], session=session)
        tax_lines = {line['record_id']: line['values'] for line in handler._get_unfold_lines(options, 'taxes_sales')}
        self.assertEqual(tax_lines[self.tax.id], {
            'tax_amount': 30, 'base_amount': 300, 'amount_total': 330,
        })
        self.assertEqual(tax_lines[0], {
            'tax_amount': 0, 'base_amount': 70, 'amount_total': 70,
        })
