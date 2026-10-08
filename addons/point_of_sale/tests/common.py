# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4
from itertools import starmap

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class CommonPosTest(AccountTestInvoicingCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def _create_company(cls, company_xmlid=None, **create_values):
        # Avoid the branch fixture, which may contain demo journal entries.
        create_values.setdefault('candidate_xmlids', (
            'base.test_company', 'base.test_company_template', 'base.test_company_template2',
        ))
        return super()._create_company(company_xmlid=company_xmlid, **create_values)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._archive_products()
        cls.env.user.group_ids |= cls.env.ref('point_of_sale.group_pos_manager')

        # Currencies - USD, EUR
        cls.company_currency = cls.company.currency_id
        cls.other_currency = cls.setup_other_currency('EUR', rates=[('2000-01-01', 0.5)], rounding=0.001)

        cls._setup_account_journals()
        cls._setup_payment_methods()
        cls._setup_pos_configs()

        # TestPoSCommon setup
        cls._setup_customers()
        cls._setup_categories()
        cls._setup_taxes()
        cls._setup_pos_products()

        # TODO-PARP:
        # cls._setup_attribute_products()
        # cls._setup_combo_product()  # will replace setup_product_combo_items

    @classmethod
    def _archive_products(cls):
        # Preserve fixtures created by another test base with the independent test user.
        cls.env['product.template'].search([
            ('available_in_pos', '=', True),
            ('create_uid', '!=', cls.env.uid),
        ])._write({'active': False})

    @classmethod
    def _setup_categories(cls):
        # PoS Categories
        cls.cat_no_tax, cls.cat_tax_five_incl, cls.cat_tax_ten_incl, cls.cat_tax_fifteen_incl = cls.env['pos.category'].create([
            {'name': 'No tax', 'sequence': 0},
            {'name': 'Tax five incl', 'sequence': 1},
            {'name': 'Tax ten incl', 'sequence': 2},
            {'name': 'Tax fifteen incl', 'sequence': 3},
        ])
        # Product Categories
        cls.categ_basic = cls.env.ref('product.product_category_services')

    @classmethod
    def _setup_pos_products(cls):
        cls.ten_dollars_no_tax = cls.create_product_template('Ten dollars no tax', 10.0, [cls.cat_no_tax.id])
        cls.twenty_dollars_no_tax = cls.create_product_template('Twenty dollars no tax', 20.0, [cls.cat_no_tax.id])
        cls.ten_dollars_with_5_incl = cls.create_product_template('Ten dollars with 5 included', 10.0, [cls.cat_tax_five_incl.id], [cls.taxes['tax5_incl'].id])
        cls.twenty_dollars_with_5_incl = cls.create_product_template('Twenty dollars with 5 included', 20.0, [cls.cat_tax_five_incl.id], [cls.taxes['tax5_incl'].id])
        cls.ten_dollars_with_10_incl = cls.create_product_template('Ten dollars with 10 included', 10.0, [cls.cat_tax_ten_incl.id], [cls.taxes['tax10_incl'].id])
        cls.twenty_dollars_with_10_incl = cls.create_product_template('Twenty dollars with 10 included', 20.0, [cls.cat_tax_ten_incl.id], [cls.taxes['tax10_incl'].id])
        cls.ten_dollars_with_15_incl = cls.create_product_template('Ten dollars with 15 included', 10.0, [cls.cat_tax_fifteen_incl.id], [cls.taxes['tax15_incl'].id])
        cls.twenty_dollars_with_15_incl = cls.create_product_template('Twenty dollars with 15 included', 20.0, [cls.cat_tax_fifteen_incl.id], [cls.taxes['tax15_incl'].id])

    @classmethod
    def _setup_customers(cls):
        (
            cls.partner_mobt, cls.partner_adgu, cls.partner_lowe, cls.partner_jcb,
            cls.partner_moda, cls.partner_stva, cls.partner_manv, cls.partner_vlst,
            cls.partner_parp,
        ) = cls.env['res.partner'].create([
            {'name': 'MOBT'}, {'name': 'ADGU'}, {'name': 'LOWE'}, {'name': 'JCB'},
            {'name': 'MODA'}, {'name': 'STVA'}, {'name': 'MANV'}, {'name': 'VLST'},
            {'name': 'PARP'},
        ])
        cls.customer = cls.env['res.partner'].create({
            'name': 'Customer 1',
            'property_account_receivable_id': cls.copy_account(cls.receivable_account, {'name': 'Customer 1 Receivable'}).id
        })
        cls.other_customer = cls.env['res.partner'].create({
            'name': 'Other Customer',
            'property_account_receivable_id': cls.env['account.account'].create({
                'name': 'Other Receivable',
                'code': 'RCV00',
                'account_type': 'asset_receivable',
                'internal_group': 'asset',
            }).id
        })

    @classmethod
    def _setup_taxes(cls):
        def create_tax(percentage, price_include_override='tax_excluded'):
            return cls.env['account.tax'].create({
                'name': f"Tax {percentage}% {'incl' if price_include_override == 'tax_excluded' else 'excl'}",
                'amount': percentage,
                'price_include_override': price_include_override,
            })
        cls.taxes = {
            'tax7': create_tax(7),
            'tax10': create_tax(10),
            'tax5_incl': create_tax(5, 'tax_included'),
            'tax10_incl': create_tax(10, 'tax_included'),
            'tax15_incl': create_tax(15, 'tax_included'),
            'tax21_incl': create_tax(21, 'tax_included'),
        }
        cls.taxes['tax_group_7_10'] = cls.env['account.tax'].create({
            'name': 'Tax 7+10 %',
            'amount_type': 'group',
            'children_tax_ids': [Command.set((cls.taxes['tax7'] + cls.taxes['tax10']).ids)]
        })

    @classmethod
    def _setup_account_journals(cls):
        cls.receivable_account = cls.company_data['default_account_receivable']

        cls.pos_receivable_cash = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Cash'})
        cls.pos_receivable_bank = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Bank'})
        cls.outstanding_bank = cls.copy_account(cls.inbound_payment_method_line.payment_account_id, {'name': 'Outstanding Bank'})

        cls.other_cash_journal = cls.env['account.journal'].create({
            'name': 'Cash Other',
            'type': 'cash',
            'company_id': cls.company.id,
            'code': 'CSHO',
            'sequence': 10,
            'currency_id': cls.other_currency.id,
        })
        cls.other_sales_journal = cls.env['account.journal'].create({
            'name': 'PoS Sale Other',
            'type': 'sale',
            'code': 'POSO',
            'company_id': cls.company.id,
            'sequence': 12,
            'currency_id': cls.other_currency.id,
        })
        cls.other_bank_journal = cls.env['account.journal'].create({
            'name': 'Bank Other',
            'type': 'bank',
            'company_id': cls.company.id,
            'code': 'BNKO',
            'sequence': 13,
            # TODO-PARP: Keep bank methods compatible with legacy tests selecting across configs.
            'currency_id': False,
        })

    @classmethod
    def _setup_payment_methods(cls):
        # drop stray payment methods not tied to a config (e.g. leftover delivery-provider ones)
        cls.env['pos.payment.method'].search([
            ('company_id', '=', cls.company.id),
            ('config_ids', '=', False),
        ]).unlink()
        cls.cash_pm = cls.env['pos.payment.method'].create({
            'name': 'Cash',
            'type': 'cash',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'journal_id': cls.company_data['default_journal_cash'].id,
            'company_id': cls.env.company.id,
        })
        cls.bank_pm = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'type': 'bank',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
        })
        cls.credit_pm = cls.env['pos.payment.method'].create({
            'name': 'Credit',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'type': 'pay_later',
        })
        # TODO-PARP: Remove these aliases after all modules are migrated.
        cls.cash_payment_method = cls.cash_pm
        cls.bank_payment_method = cls.bank_pm
        cls.credit_payment_method = cls.credit_pm
        cls.cash_pm1 = cls.cash_pm
        cls.bank_pm1 = cls.bank_pm
        cls.pay_later_pm = cls.credit_pm

        cls.cash_pm2 = cls.env['pos.payment.method'].create({
            'name': 'Cash Other',
            'type': 'cash',
            'journal_id': cls.other_cash_journal.id,
            'receivable_account_id': cls.pos_receivable_cash.id,
        })
        cls.bank_pm2 = cls.env['pos.payment.method'].create({
            'name': 'Bank Other',
            'type': 'bank',
            'journal_id': cls.other_bank_journal.id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
        })

    @classmethod
    def _setup_pos_configs(cls):
        cls.pos_config_usd = cls.env['pos.config'].create({
            'name': 'PoS Config USD',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'payment_method_ids': [
                (4, cls.credit_pm.id),
                (4, cls.bank_pm.id),
                (4, cls.cash_pm.id),
            ],
        })

        cls.pricelist_eur = cls.env['product.pricelist'].create({
            'name': 'Test EUR Pricelist',
            'currency_id': cls.other_currency.id,
        })

        cls.pos_config_eur = cls.env['pos.config'].create({
            'name': 'PoS Config EUR',
            'journal_id': cls.other_sales_journal.id,
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, cls.pricelist_eur.ids)],
            'pricelist_id': cls.pricelist_eur.id,
            'payment_method_ids': [Command.set((cls.bank_pm2 | cls.bank_pm).ids)],
        })
        # TODO-PARP: Remove this alias after all modules are migrated.
        cls.basic_config = cls.pos_config_usd

    @classmethod
    def create_product_template(cls, name, list_price, pos_categ_ids=[], tax_ids=[], **kwargs):
        return cls.env['product.template'].create({
            'available_in_pos': True,
            'name': name,
            'list_price': list_price,
            'taxes_id': [Command.set(list(tax_ids))],
            'pos_categ_ids': [Command.set(list(pos_categ_ids))],
            **kwargs,
        })

    @classmethod
    def create_product(cls, name, category, lst_price, standard_price=None, tax_ids=[], sale_account=None):
        product = cls.env['product.product'].create({
            'is_storable': True,
            'available_in_pos': True,
            'taxes_id': [Command.set(list(tax_ids))],
            'name': name,
            'categ_id': category.id,
            'lst_price': lst_price,
            'standard_price': standard_price or 0.0,
            'company_id': cls.env.company.id,
        })
        if sale_account:
            product.property_account_income_id = sale_account
        return product

    def open_new_session(self, opening_cash=0, config=None):
        """ Used to open new pos session in each configuration.
        The configuration defaults to self.pos_config_usd.
        - The idea is to properly set values that are constant
          and commonly used in an open pos session.
        Fields:
            * config : the pos.config passed to this helper.
            * pos_session : the current_session_id of config
            * currency : currency of the current pos.session
            * pricelist : the default pricelist of the session
        """
        config = config or self.pos_config_usd
        config.open_ui()
        self.pos_session = config.current_session_id
        self.currency = self.pos_session.currency_id
        self.pricelist = self.pos_session.config_id.pricelist_id
        self.pos_session.set_opening_control(opening_cash, None)
        return self.pos_session

    def close_pos_session(self, config=None, amount=None):
        config = config or self.pos_config_usd
        session = config.current_session_id
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
        for order_id in self.env['pos.order'].browse(order_ids):
            result[order_id.uuid] = order_id
        return result

    def create_pos_order(self, lines, payments=None, customer=False, **kwargs):
        order_data = self._create_ui_order_data(lines, payments, customer, **kwargs)
        order_id = self.env['pos.order'].sync_from_ui([order_data])['pos.order'][0]['id']
        return self.env['pos.order'].browse(order_id)

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
        cls.pos_receivable_account = cls.company.account_default_pos_receivable_account_id
        cls.sale_account = cls.company.income_account_id

        # TODO-PARP: Prepare the session journal before legacy POS users close sessions.
        cls.env['account.journal']._ensure_company_account_journal()

        # TODO-PARP: Keep the legacy pricelist setup until all modules are migrated.
        cls.group_user._apply_group(cls.group_product_pricelist)
        pricelist = cls.env['product.pricelist'].with_context(active_test=False).search([
            ('currency_id', '=', cls.company_currency.id),
            ('company_id', 'in', [False, cls.company.id]),
            ('item_ids', '=', False),
        ], limit=1)
        if not pricelist:
            pricelist = cls.env['product.pricelist'].create({
                'name': 'Test Pricelist',
                'currency_id': cls.company_currency.id,
            })
        pricelist.active = True
        cls.basic_config.write({
            'pricelist_id': pricelist.id,
            'available_pricelist_ids': [Command.set(pricelist.ids)],
        })

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


# TODO-PARP: Remove usage of `archive_products` from other `setUpClass` (use the existing products)
def archive_products(env):
    # Archive all existing product to avoid noise during the tours
    all_pos_product = env['product.template'].search([('available_in_pos', '=', True)])
    all_pos_product._write({'active': False})
