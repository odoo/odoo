# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
from itertools import starmap
from uuid import uuid4

from odoo import Command, fields
from odoo.tests import HttpCase

from odoo.addons.point_of_sale.tests.common_fixture import PosTestRecords
from odoo.addons.account.tests.common import TestTaxCommon


class CommonPosTest(PosTestRecords):

    def open_new_session(self, opening_cash=0, config=None):
        config = config or self.pos_config_usd
        config.open_ui()
        self.pos_session = config.current_session_id
        self.pos_session.set_opening_control(opening_cash, None)
        return self.pos_session

    def close_pos_session(self, config=None, amount=None):
        config = config or self.pos_config_usd
        session = config.current_session_id
        if draft_orders := session.order_ids.filtered(lambda o: o.state == 'draft'):
            draft_orders.with_context(active_ids=draft_orders.ids).action_pos_order_cancel()

        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        payment_method_closing = {}
        if cash_details.get('id'):
            payment_method_closing[cash_details['id']] = cash_details['payment_amount'] if amount is None else amount
        session.close_session_from_ui(payment_method_closing)
        self.assertEqual(session.state, 'closed')
        return session

    def _create_ui_order_data(self, lines, payments=None, customer=False, config=False, **kwargs):
        config = config or self.pos_config_usd
        if not config.current_session_id:
            config.open_ui()
        fiscal_position = (
            self.env['account.fiscal.position'].browse(kwargs['fiscal_position_id'])
            if 'fiscal_position_id' in kwargs
            else customer.property_account_position_id if customer else config.default_fiscal_position_id
        )

        def _create_order_line(product, quantity=1.0, discount=0.0, line_kwargs={}):
            price_unit = line_kwargs.get('price_unit', config.pricelist_id._get_product_price(product, quantity))
            tax_ids = fiscal_position.map_tax(product.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.env.company)))
            price_unit_after_discount = price_unit * (1 - discount / 100.0)
            tax_values = (
                tax_ids.compute_all(price_unit_after_discount, config.currency_id, quantity)
                if tax_ids
                else {
                    'total_excluded': price_unit_after_discount * quantity,
                    'total_included': price_unit_after_discount * quantity,
                }
            )
            return list(Command.create({
                'price_unit': price_unit,
                'product_id': product.id,
                'full_product_name': product.name,
                'price_subtotal': abs(tax_values['total_excluded']),  # Must never be negative, qty is used to determine the sign of the amounts
                'price_subtotal_incl': abs(tax_values['total_included']),  # Must never be negative, qty is used to determine the sign of the amounts
                'qty': quantity,
                'discount': discount,
                'tax_ids': [(6, 0, tax_ids.ids)],
                'uuid': str(uuid4()),
                **line_kwargs,
            }))

        order_lines = [list(command) for command in starmap(_create_order_line, lines)]

        # 2. generate the payments
        if payments is None and kwargs.get('state', 'paid') != 'draft':
            def _get_line_amount_incl(line):
                vals = line[2]
                qty, price_unit = vals.get('qty', 1.0), vals.get('price_unit', 1.0)
                amount = vals.get('price_subtotal_incl', abs(price_unit * qty))
                return amount * (-1 if (price_unit < 0) ^ (qty < 0) else 1)

            total_amount_incl = config.currency_id.round(sum(_get_line_amount_incl(line) for line in order_lines))
            payments = [[config.payment_method_ids[0], total_amount_incl]]

        def _create_payment(payment_method, amount, payment_kwargs=None):
            return list(Command.create({
                'amount': amount,
                'payment_method_id': payment_method.id,
                'uuid': str(uuid4()),
                **(payment_kwargs or {}),
            }))

        # 3. complete the fields of the order_data
        order_uuid = str(uuid4())
        return {
            'amount_paid': 0.0,  # calculation is done via _compute_prices
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': fiscal_position.id,
            'pricelist_id': config.pricelist_id.id,
            'name': 'Order %s' % order_uuid,
            'lines': order_lines,
            'partner_id': customer and customer.id,
            'session_id': config.current_session_id.id,
            'company_id': config.company_id.id,
            'payment_ids': list(starmap(_create_payment, payments or [])),
            'uuid': order_uuid,
            'user_id': self.env.uid,
            **kwargs,
        }

    def create_orders(self, order_data_params):
        """Returns a dict mapping uuid to its created pos.order record."""
        result = {}
        order_data = [self._create_ui_order_data(**params) for params in order_data_params]
        order_ids = [order['id'] for order in self.env['pos.order'].sync_from_ui(order_data)['pos.order']]
        for order in self.env['pos.order'].browse(order_ids).exists():
            order._compute_prices()
            result[order.uuid] = order
        return result

    def create_pos_order(self, lines, payments=None, customer=False, **kwargs):
        order_data = self._create_ui_order_data(lines, payments, customer, **kwargs)
        order_id = self.env['pos.order'].sync_from_ui([order_data])['pos.order'][0]['id']
        order = self.env['pos.order'].browse(order_id).exists()
        order._compute_prices()
        return order

    def refund_pos_order(self, order, payment_method, amount):
        refund_action = order.refund()
        refund_order = self.env['pos.order'].browse(refund_action['res_id'])

        if order.to_invoice:
            refund_order.to_invoice = True

        self.make_payment(refund_order, payment_method, amount)
        return refund_order

    def make_payment(self, order, payment_method, amount):
        """Make payment for the order using the given payment method."""
        payment_context = {'active_id': order.id, 'active_ids': order.ids}
        return self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': amount,
            'payment_method_id': payment_method.id,
        }).check()

    def compute_tax(self, product, price, qty=1, taxes=None, pos_config=None):
        config = pos_config or self.pos_config_usd
        if not taxes:
            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id)
        currency = config.currency_id
        res = taxes.compute_all(price, currency, qty, product=product)
        untax = res['total_excluded']
        return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

    def _remove_on_payment_taxes(self):
        """ Call this when testing the res.config.settings with Form.
            The `on_payment` taxes need to be removed, otherwise, a warning will show in the log.
        """
        self.env['account.tax'].search([
            ('company_id', '=', self.env.company.id),
            ('tax_exigibility', '=', 'on_payment')
        ]).unlink()

    # TODO-PARP: Replace this with create_pos_order
    def create_backend_pos_order(self, data):
        pos_config = data.get('pos_config', self.pos_config_usd)
        order_data = data.get('order_data', {})
        # TODO-PARP: Legacy backend callers supply a pricelist independently of the config.
        # Align the existing config with that pricelist until those callers are migrated.
        pricelist = self.env['product.pricelist'].browse(order_data.get('pricelist_id'))
        if pricelist and pricelist.currency_id != pos_config.currency_id:
            pos_config.journal_id.currency_id = pricelist.currency_id
            pos_config.write({
                'pricelist_id': pricelist.id,
                'available_pricelist_ids': [Command.set(pricelist.ids)],
            })
        line_product_ids = [line_data['product_id'] for line_data in data.get('line_data', [])]
        product_by_id = {p.id: p for p in self.env['product.product'].browse(line_product_ids)}
        refund = False

        if not pos_config.current_session_id:
            pos_config.open_ui()

        order = self.env['pos.order'].create({
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'company_id': pos_config.company_id.id,
            'session_id': pos_config.current_session_id.id,
            'lines': [
                Command.create({
                    'price_unit': product_by_id[line_data['product_id']].lst_price,
                    'price_subtotal': product_by_id[line_data['product_id']].lst_price,
                    'tax_ids': [(6, 0, product_by_id[line_data['product_id']].taxes_id.ids)],
                    'price_subtotal_incl': 0,
                    **line_data,
                }) for line_data in data.get('line_data', [])
            ],
            **order_data,
        })

        # Re-trigger prices computation
        order.lines._onchange_amount_line_all()
        order._compute_prices()

        if data.get('payment_data'):
            payment_context = {"active_ids": order.ids, "active_id": order.id}
            for payment in data['payment_data']:
                make_payment = {'payment_method_id': payment['payment_method_id']}
                if payment.get('amount'):
                    make_payment['amount'] = payment['amount']
                order_payment = self.env['pos.make.payment'].with_context(**payment_context).create(make_payment)
                order_payment.with_context(**payment_context).check()

        if data.get('refund_data'):
            refund_action = order.refund()
            refund = self.env['pos.order'].browse(refund_action['res_id'])
            payment_context = {"active_ids": refund.ids, "active_id": refund.id}

            if data.get('order_data') and data['order_data'].get('to_invoice', False):
                refund.to_invoice = True

            for refund_data in data['refund_data']:
                make_refund = {'payment_method_id': refund_data['payment_method_id']}
                if refund_data.get('amount'):
                    make_refund['amount'] = refund_data['amount']
                refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create(make_refund)
                refund_payment.with_context(**payment_context).check()

        return order, refund

    def _get_loaded_product_ids(self, session):
        data = session.load_data()
        special_product = session.config_id._get_special_products().ids
        return [p['product_variant_ids'][0] for p in data['product.template']['records']
                if p['active'] and p['product_variant_ids'][0] not in special_product]


class PosHttpCommon(CommonPosTest, HttpCase):

    @classmethod
    def _get_main_company(cls):
        return cls.company_data['company']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_users()
        main_company = cls._get_main_company()
        cls.http_pricelists.currency_id = main_company.currency_id

        cls.account_receivable = cls.pos_receivable_account
        cls.bank_pm.write({
            'receivable_account_id': False,
            'outstanding_account_id': cls.inbound_payment_method_line.payment_account_id.id,
        })
        cls.cash_pm.receivable_account_id = cls.account_receivable

        # The pen's surcharge is only used by HTTP product tours.
        cls.whiteboard_pen.attribute_line_ids.product_template_value_ids[0].price_extra = 2

        for product, price in [
            (cls.whiteboard_pen, 1.20), (cls.wall_shelf, 1.98), (cls.small_shelf, 2.83),
            (cls.magnetic_board, 1.98), (cls.monitor_stand, 3.19), (cls.desk_pad, 1.98),
            (cls.letter_tray, 4.80), (cls.desk_organizer, 5.10),
        ]:
            product.write({
                'list_price': price,
                'taxes_id': [Command.clear()],
            })

        source_tax = cls.taxes['tax10']
        source_tax.write({'name': 'SRC', 'fiscal_position_ids': [Command.set(main_company.domestic_fiscal_position_id.ids)]})
        for tax, name, amount in [(cls.taxes['tax5_incl'], 'DST', 5), (cls.taxes['tax7'], 'DST2', 10)]:
            tax.write({
                'name': name,
                'amount': amount,
                'price_include_override': 'tax_excluded',
                'fiscal_position_ids': [Command.set(cls.fiscal_position_pos.ids)],
                'original_tax_ids': [Command.set(source_tax.ids)],
            })
        cls.letter_tray.taxes_id = source_tax

    def start_pos_tour(self, tour_name, login='pos_user', **kwargs):
        pos_config = kwargs.get('pos_config') or self.main_pos_config
        url = f'/pos/ui/{pos_config.id}'
        self.start_tour(url, tour_name, login=login, **kwargs)

    def get_method_additional_tags(self, test_method):
        additional_tags = super().get_method_additional_tags(test_method)
        method_source = inspect.getsource(test_method)
        if "self.start_pos_tour" in method_source:
            additional_tags.append("is_tour")
        return additional_tags


class TestTaxCommonPOS(PosHttpCommon, TestTaxCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Accounting tax scenarios expect cent rounding for the shared EUR currency.
        cls.other_currency.rounding = 0.01
        cls.partner_a.name = "AAAAAA"  # The POS only load the first 100 partners

    def create_base_line_product(self, base_line, **kwargs):
        return self.env['product.product'].create({
            **kwargs,
            'available_in_pos': True,
            'list_price': base_line['price_unit'],
            'taxes_id': [Command.set(base_line['tax_ids'].ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
            'company_id': self.env.company.id,
        })

    def ensure_products_on_document(self, document, product_prefix):
        for i, base_line in enumerate(document['lines'], start=1):
            base_line['product_id'] = self.create_base_line_product(base_line, name=f'{product_prefix}_{i}')

    def assert_pos_order_totals(self, order, expected_values):
        expected_amounts = {}
        if 'tax_amount_currency' in expected_values:
            expected_amounts['amount_tax'] = expected_values['tax_amount_currency']
        if 'total_amount_currency' in expected_values:
            expected_amounts['amount_total'] = expected_values['total_amount_currency']
        self.assertRecordValues(order, [expected_amounts])

    def assert_pos_orders_and_invoices(self, tour, tests_with_orders):
        if self.main_pos_config.current_session_id:
            self.close_pos_session()

        self.start_pos_tour(tour)
        orders = self.env['pos.order'].search([('session_id', '=', self.main_pos_config.current_session_id.id)], limit=len(tests_with_orders))
        for index, (order, (test_code, _document, _soft_checking, _amount_type, _amount, expected_values)) in enumerate(zip(orders, tests_with_orders)):
            with self.subTest(test_code=test_code, index=index):
                self.assert_pos_order_totals(order, expected_values)
                if order.account_move:
                    self.assert_invoice_totals(order.account_move, expected_values)

        self.close_pos_session()


# TODO-PARP: Replace usage of this with `CommonPosTest`
class TestPoSCommon(CommonPosTest):
    """Temporary compatibility layer for existing POS test imports.

        # TODO-PARP:
        Migration Check List:
        - Replace create_ui_order_data + sync_from_ui -> create_orders
        - Replace create_backend_pos_order -> create_pos_order + refund_pos_order (if required)
        - Use create_pos_order for hard coaded order creation
        - Make use of refund_pos_order
    """
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.basic_config = cls.pos_config_usd
        cls.other_currency_config = cls.pos_config_eur
        # TODO-PARP: Remove this alias after all modules are migrated.
        cls.account_tax_return_journal = cls.company_data['default_journal_misc']
        cls.tax_received_account = cls.company_data['default_account_tax_sale']
        cls.sales_account = cls.company_data['default_account_revenue']
        cls.sale_account = cls.company.income_account_id

        # TODO-PARP: Prepare the session journal before legacy POS users close sessions.
        cls.env['account.journal']._ensure_company_account_journal()

        cls.group_user._apply_group(cls.group_product_pricelist)

        # TODO-PARP: Remove these legacy tax fixtures after all modules are migrated.
        cls.taxes['tax21'] = cls.taxes['tax21_incl']
        cls.taxes['tax21'].price_include_override = 'tax_excluded'
        cls.taxes.update(dict(zip(
            ('tax_fixed006', 'tax_fixed012'),
            cls.env['account.tax'].create([
                {'name': 'Tax 0.06', 'amount_type': 'fixed', 'amount': 0.06, 'price_include_override': 'tax_excluded'},
                {'name': 'Tax 0.12', 'amount_type': 'fixed', 'amount': 0.12, 'price_include_override': 'tax_excluded'},
            ]),
        )))

    # TODO-PARP: Move remaining TestPoSCommon helpers here.
    #
    # Payments/accounting:
    # - _run_test()
    # - _check_invoice_journal_entries()
    # - _check_session_journal_entries()
    # - _find_then_assert_values()
    # - _assert_account_move()

    # TODO-PARP: Remove this compatibility helper after all modules are migrated.
    def create_ui_order_data(self, pos_order_lines_ui_args, pos_order_ui_args=None, customer=False, is_invoiced=False, payments=None, uuid=None):
        order_args = {'to_invoice': is_invoiced, **(pos_order_ui_args or {})}
        if uuid:
            order_args['uuid'] = uuid

        lines = []
        for line in pos_order_lines_ui_args:
            if isinstance(line, dict):
                line_args = dict(line)
                lines.append((
                    line_args.pop('product'), line_args.pop('quantity'),
                    line_args.pop('discount', 0.0), line_args,
                ))
            else:
                lines.append(line)

        order_data = self._create_ui_order_data(lines, payments, customer, self.config, **order_args)
        total_included = total_excluded = 0.0
        for line in order_data['lines']:
            values = line[2]
            sign = -1 if (values['price_unit'] < 0) ^ (values['qty'] < 0) else 1
            total_included += sign * values['price_subtotal_incl']
            total_excluded += sign * values['price_subtotal']

        if payments is None and order_data['payment_ids']:
            cash_pm = self.config._get_cash_payment_method()
            if not cash_pm:
                raise Exception('There should be a cash payment method set in the pos.config.')
            order_data['payment_ids'][0][2].update({
                'payment_method_id': cash_pm.id,
                'amount': total_included,
            })

        order_data.update({
            'amount_paid': sum(payment[2]['amount'] for payment in order_data['payment_ids']),
            'amount_total': total_included,
            'amount_tax': total_included - total_excluded,
            **order_args,
        })
        return order_data

    def _create_orders(self, order_data_params):
        '''Returns a dict mapping uuid to its created pos.order record.'''
        result = {}
        order_data = [self.create_ui_order_data(**params) for params in order_data_params]
        order_ids = [order['id'] for order in self.env['pos.order'].sync_from_ui(order_data)['pos.order']]
        for order_id in self.env["pos.order"].browse(order_ids):
            result[order_id.uuid] = order_id
        return result

    @classmethod
    def create_product(cls, name, category, lst_price, standard_price=None, tax_ids=[], sale_account=None):
        product = super().create_product(
            name,
            lst_price,
            tax_ids,
            categ_id=category.id,
            standard_price=standard_price or 0.0
        )
        if sale_account:
            product.property_account_income_id = sale_account
        return product


# TODO-PARP: Remove usage of `archive_products` from other `setUpClass` (use the existing products)
def archive_products(env):
    # Archive all existing product to avoid noise during the tours
    all_pos_product = env['product.template'].search([('available_in_pos', '=', True)])
    all_pos_product._write({'active': False})
