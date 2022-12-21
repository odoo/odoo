# -*- coding: utf-8 -*-
from random import randint
from datetime import datetime

from odoo import fields, tools
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests.common import Form
from odoo.tests import tagged

import logging

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestPointOfSaleCommon(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'point_of_sale_update_stock_quantities': 'real',
        })

        cls.AccountBankStatement = cls.env['account.bank.statement']
        cls.AccountBankStatementLine = cls.env['account.bank.statement.line']
        cls.PosMakePayment = cls.env['pos.make.payment']
        cls.PosOrder = cls.env['pos.order']
        cls.PosSession = cls.env['pos.session']
        cls.company = cls.company_data['company']
        cls.product3 = cls.env['product.product'].create({
            'name': 'Product 3',
            'list_price': 450,
        })
        cls.product4 = cls.env['product.product'].create({
            'name': 'Product 4',
            'list_price': 750,
        })
        cls.partner1 = cls.env['res.partner'].create({'name': 'Partner 1'})
        cls.partner4 = cls.env['res.partner'].create({'name': 'Partner 4'})
        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Main',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'invoice_journal_id': cls.company_data['default_journal_sale'].id,
        })
        cls.led_lamp = cls.env['product.product'].create({
            'name': 'LED Lamp',
            'available_in_pos': True,
            'list_price': 0.90,
        })
        cls.whiteboard_pen = cls.env['product.product'].create({
            'name': 'Whiteboard Pen',
            'available_in_pos': True,
            'list_price': 1.20,
        })
        cls.newspaper_rack = cls.env['product.product'].create({
            'name': 'Newspaper Rack',
            'available_in_pos': True,
            'list_price': 1.28,
        })
        cls.cash_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Cash',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'journal_id': cls.company_data['default_journal_cash'].id,
            'company_id': cls.env.company.id,
        })
        cls.bank_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'company_id': cls.env.company.id,
        })
        cls.credit_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Credit',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'split_transactions': True,
            'company_id': cls.env.company.id,
        })
        cls.pos_config.write({'payment_method_ids': [(4, cls.credit_payment_method.id), (4, cls.bank_payment_method.id), (4, cls.cash_payment_method.id)]})

        # Create POS journal
        cls.pos_config.journal_id = cls.env['account.journal'].create({
            'type': 'general',
            'name': 'Point of Sale - Test',
            'code': 'POSS - Test',
            'company_id': cls.env.company.id,
            'sequence': 20
        })

        # create a VAT tax of 10%, included in the public price
        Tax = cls.env['account.tax']
        account_tax_10_incl = Tax.create({
            'name': 'VAT 10 perc Incl',
            'amount_type': 'percent',
            'amount': 10.0,
            'price_include': True,
        })

        # assign this 10 percent tax on the [PCSC234] PC Assemble SC234 product
        # as a sale tax
        cls.product3.taxes_id = [(6, 0, [account_tax_10_incl.id])]

        # create a VAT tax of 5%, which is added to the public price
        account_tax_05_incl = Tax.create({
            'name': 'VAT 5 perc Incl',
            'amount_type': 'percent',
            'amount': 5.0,
            'price_include': False,
        })

        # create a second VAT tax of 5% but this time for a child company, to
        # ensure that only product taxes of the current session's company are considered
        #(this tax should be ignore when computing order's taxes in following tests)
        account_tax_05_incl_chicago = Tax.create({
            'name': 'VAT 05 perc Excl (US)',
            'amount_type': 'percent',
            'amount': 5.0,
            'price_include': False,
            'company_id': cls.company_data_2['company'].id,
        })

        cls.product4.company_id = False
        # I assign those 5 percent taxes on the PCSC349 product as a sale taxes
        cls.product4.write(
            {'taxes_id': [(6, 0, [account_tax_05_incl.id, account_tax_05_incl_chicago.id])]})

        # Set account_id in the generated repartition lines. Automatically, nothing is set.
        invoice_rep_lines = (account_tax_05_incl | account_tax_10_incl).mapped('invoice_repartition_line_ids')
        refund_rep_lines = (account_tax_05_incl | account_tax_10_incl).mapped('refund_repartition_line_ids')

        # Expense account, should just be something else than receivable/payable
        (invoice_rep_lines | refund_rep_lines).write({'account_id': cls.company_data['default_account_tax_sale'].id})


@tagged('post_install', '-at_install')
class TestPoSCommon(ValuationReconciliationTestCommon):
    """ Set common values for different special test cases.

    The idea is to set up common values here for the tests
    and implement different special scenarios by inheriting
    this class.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'point_of_sale_update_stock_quantities': 'real',
            'country_id': cls.env['res.country'].create({
                'name': 'PoS Land',
                'code': 'WOW',
            }),
        })

        # Set basic defaults
        cls.company = cls.company_data['company']
        cls.pos_sale_journal = cls.env['account.journal'].create({
            'type': 'general',
            'name': 'Point of Sale Test',
            'code': 'POSS',
            'company_id': cls.company.id,
            'sequence': 20
        })
        cls.sales_account = cls.company_data['default_account_revenue']
        cls.invoice_journal = cls.company_data['default_journal_sale']
        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.tax_received_account = cls.company_data['default_account_tax_sale']
        cls.company.account_default_pos_receivable_account_id = cls.env['account.account'].create({
            'code': 'X1012 - POS',
            'name': 'Debtors - (POS)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_receivable').id,
        })
        cls.pos_receivable_account = cls.company.account_default_pos_receivable_account_id
        cls.pos_receivable_cash = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Cash'})
        cls.pos_receivable_bank = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Bank'})
        cls.outstanding_bank = cls.copy_account(cls.company.account_journal_payment_debit_account_id, {'name': 'Outstanding Bank'})
        cls.c1_receivable = cls.copy_account(cls.receivable_account, {'name': 'Customer 1 Receivable'})
        cls.other_receivable_account = cls.env['account.account'].create({
            'name': 'Other Receivable',
            'code': 'RCV00' ,
            'user_type_id': cls.env['account.account.type'].create({'name': 'RCV type', 'type': 'receivable', 'internal_group': 'asset'}).id,
            'internal_group': 'asset',
            'reconcile': True,
        })

        # company_currency can be different from `base.USD` depending on the localization installed
        cls.company_currency = cls.company.currency_id
        # other_currency is a currency different from the company_currency
        # sometimes company_currency is different from USD, so handle appropriately.
        cls.other_currency = cls.currency_data['currency']

        cls.currency_pricelist = cls.env['product.pricelist'].create({
            'name': 'Public Pricelist',
            'currency_id': cls.company_currency.id,
        })
        # Set Point of Sale configurations
        # basic_config
        #   - derived from 'point_of_sale.pos_config_main' with added invoice_journal_id and credit payment method.
        # other_currency_config
        #   - pos.config set to have currency different from company currency.
        cls.basic_config = cls._create_basic_config()
        cls.other_currency_config = cls._create_other_currency_config()

        # Set product categories
        # categ_basic
        #   - just the plain 'product.product_category_all'
        # categ_anglo
        #   - product category with fifo and real_time valuations
        #   - used for checking anglo saxon accounting behavior
        cls.categ_basic = cls.env.ref('product.product_category_all')
        cls.env.company.anglo_saxon_accounting = True
        cls.categ_anglo = cls._create_categ_anglo()

        # other basics
        cls.sale_account = cls.categ_basic.property_account_income_categ_id
        cls.other_sale_account = cls.env['account.account'].search([
            ('company_id', '=', cls.company.id),
            ('user_type_id', '=', cls.env.ref('account.data_account_type_revenue').id),
            ('id', '!=', cls.sale_account.id)
        ], limit=1)

        # Set customers
        cls.customer = cls.env['res.partner'].create({'name': 'Customer 1', 'property_account_receivable_id': cls.c1_receivable.id})
        cls.other_customer = cls.env['res.partner'].create({'name': 'Other Customer', 'property_account_receivable_id': cls.other_receivable_account.id})

        # Set taxes
        # cls.taxes => dict
        #   keys: 'tax7', 'tax10'(price_include=True), 'tax_group_7_10'
        cls.taxes = cls._create_taxes()

        cls.stock_location_components = cls.env["stock.location"].create({
            'name': 'Shelf 1',
            'location_id': cls.company_data['default_warehouse'].lot_stock_id.id,
        })


    #####################
    ## private methods ##
    #####################

    @classmethod
    def _create_basic_config(cls):
        new_config = Form(cls.env['pos.config'])
        new_config.name = 'PoS Shop Test'
        new_config.module_account = True
        new_config.invoice_journal_id = cls.invoice_journal
        new_config.journal_id = cls.pos_sale_journal
        new_config.available_pricelist_ids.clear()
        new_config.available_pricelist_ids.add(cls.currency_pricelist)
        new_config.pricelist_id = cls.currency_pricelist
        config = new_config.save()
        cls.cash_pm1 = cls.env['pos.payment.method'].create({
            'name': 'Cash',
            'journal_id': cls.company_data['default_journal_cash'].id,
            'receivable_account_id': cls.pos_receivable_cash.id,
            'company_id': cls.env.company.id,
        })
        cls.bank_pm1 = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
            'company_id': cls.env.company.id,
        })
        cls.cash_split_pm1 = cls.cash_pm1.copy(default={
            'name': 'Split (Cash) PM',
            'split_transactions': True,
        })
        cls.bank_split_pm1 = cls.bank_pm1.copy(default={
            'name': 'Split (Bank) PM',
            'split_transactions': True,
        })
        cls.pay_later_pm = cls.env['pos.payment.method'].create({'name': 'Pay Later', 'split_transactions': True})
        config.write({'payment_method_ids': [(4, cls.cash_split_pm1.id), (4, cls.bank_split_pm1.id), (4, cls.cash_pm1.id), (4, cls.bank_pm1.id), (4, cls.pay_later_pm.id)]})
        return config

    @classmethod
    def _create_other_currency_config(cls):
        (cls.other_currency.rate_ids | cls.company_currency.rate_ids).unlink()
        cls.env['res.currency.rate'].create({
            'rate': 0.5,
            'currency_id': cls.other_currency.id,
            'name': datetime.today().date(),
        })
        other_cash_journal = cls.env['account.journal'].create({
            'name': 'Cash Other',
            'type': 'cash',
            'company_id': cls.company.id,
            'code': 'CSHO',
            'sequence': 10,
            'currency_id': cls.other_currency.id
        })
        other_invoice_journal = cls.env['account.journal'].create({
            'name': 'Customer Invoice Other',
            'type': 'sale',
            'company_id': cls.company.id,
            'code': 'INVO',
            'sequence': 11,
            'currency_id': cls.other_currency.id
        })
        other_sales_journal = cls.env['account.journal'].create({
            'name':'PoS Sale Other',
            'type': 'sale',
            'code': 'POSO',
            'company_id': cls.company.id,
            'sequence': 12,
            'currency_id': cls.other_currency.id
        })
        other_bank_journal = cls.env['account.journal'].create({
            'name': 'Bank Other',
            'type': 'bank',
            'company_id': cls.company.id,
            'code': 'BNKO',
            'sequence': 13,
            'currency_id': cls.other_currency.id
        })
        other_pricelist = cls.env['product.pricelist'].create({
            'name': 'Public Pricelist Other',
            'currency_id': cls.other_currency.id,
        })
        cls.cash_pm2 = cls.env['pos.payment.method'].create({
            'name': 'Cash Other',
            'journal_id': other_cash_journal.id,
            'receivable_account_id': cls.pos_receivable_cash.id,
        })
        cls.bank_pm2 = cls.env['pos.payment.method'].create({
            'name': 'Bank Other',
            'journal_id': other_bank_journal.id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
        })

        new_config = cls.env['pos.config'].create({
            'name': 'Shop Other',
            'invoice_journal_id': other_invoice_journal.id,
            'journal_id': other_sales_journal.id,
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, [other_pricelist.id])],
            'pricelist_id': other_pricelist.id,
            'payment_method_ids': [(6, 0, [cls.cash_pm2.id, cls.bank_pm2.id])],
        })
        return new_config

    @classmethod
    def _create_categ_anglo(cls):
        return cls.env['product.category'].create({
            'name': 'Anglo',
            'parent_id': False,
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': cls.company_data['default_account_stock_in'].id,
            'property_stock_account_output_categ_id': cls.company_data['default_account_stock_out'].id,
        })

    @classmethod
    def _create_taxes(cls):
        """ Create taxes

        tax7: 7%, excluded in product price
        tax10: 10%, included in product price
        tax21: 21%, included in product price
        """
        def create_tag(name):
            return cls.env['account.account.tag'].create({
                'name': name,
                'applicability': 'taxes',
                'country_id': cls.env.company.country_id.id
            })

        cls.tax_tag_invoice_base = create_tag('Invoice Base tag')
        cls.tax_tag_invoice_tax = create_tag('Invoice Tax tag')
        cls.tax_tag_refund_base = create_tag('Refund Base tag')
        cls.tax_tag_refund_tax = create_tag('Refund Tax tag')

        def create_tax(percentage, price_include=False):
            return cls.env['account.tax'].create({
                'name': f'Tax {percentage}%',
                'amount': percentage,
                'price_include': price_include,
                'amount_type': 'percent',
                'include_base_amount': False,
                'invoice_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, cls.tax_tag_invoice_base.ids)],
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_received_account.id,
                        'tag_ids': [(6, 0, cls.tax_tag_invoice_tax.ids)],
                    }),
                ],
                'refund_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, cls.tax_tag_refund_base.ids)],
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_received_account.id,
                        'tag_ids': [(6, 0, cls.tax_tag_refund_tax.ids)],
                    }),
                ],
            })
        def create_tax_fixed(amount, price_include=False):
            return cls.env['account.tax'].create({
                'name': f'Tax fixed amount {amount}',
                'amount': amount,
                'price_include': price_include,
                'include_base_amount': price_include,
                'amount_type': 'fixed',
                'invoice_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, cls.tax_tag_invoice_base.ids)],
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_received_account.id,
                        'tag_ids': [(6, 0, cls.tax_tag_invoice_tax.ids)],
                    }),
                ],
                'refund_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, cls.tax_tag_refund_base.ids)],
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_received_account.id,
                        'tag_ids': [(6, 0, cls.tax_tag_refund_tax.ids)],
                    }),
                ],
            })

        tax_fixed006 = create_tax_fixed(0.06, price_include=True)
        tax_fixed012 = create_tax_fixed(0.12, price_include=True)
        tax7 = create_tax(7, price_include=False)
        tax10 = create_tax(10, price_include=True)
        tax21 = create_tax(21, price_include=True)


        tax_group_7_10 = tax7.copy()
        with Form(tax_group_7_10) as tax:
            tax.name = 'Tax 7+10%'
            tax.amount_type = 'group'
            tax.children_tax_ids.add(tax7)
            tax.children_tax_ids.add(tax10)

        return {
            'tax7': tax7,
            'tax10': tax10,
            'tax21': tax21,
            'tax_fixed006': tax_fixed006,
            'tax_fixed012': tax_fixed012,
            'tax_group_7_10': tax_group_7_10
        }

    ####################
    ## public methods ##
    ####################

    def create_random_uid(self):
        return ('%05d-%03d-%04d' % (randint(1, 99999), randint(1, 999), randint(1, 9999)))

    def create_ui_order_data(self, pos_order_lines_ui_args, customer=False, is_invoiced=False, payments=None, uid=None):
        """ Mocks the order_data generated by the pos ui.

        This is useful in making orders in an open pos session without making tours.
        Its functionality is tested in test_pos_create_ui_order_data.py.

        Before use, make sure that self is set with:
            1. pricelist -> the pricelist of the current session
            2. currency -> currency of the current session
            3. pos_session -> the current session, equivalent to config.current_session_id
            4. cash_pm -> first cash payment method in the current session
            5. config -> the active pos.config

        The above values should be set when `self.open_new_session` is called.

        :param list(tuple) pos_order_lines_ui_args: pairs of `ordered product` and `quantity`
        or triplet of `ordered product`, `quantity` and discount
        :param list(tuple) payments: pair of `payment_method` and `amount`
        """
        default_fiscal_position = self.config.default_fiscal_position_id
        fiscal_position = customer.property_account_position_id if customer else default_fiscal_position

        def create_order_line(product, quantity, discount=0.0):
            price_unit = self.pricelist.get_product_price(product, quantity, False)
            tax_ids = fiscal_position.map_tax(product.taxes_id)
            price_unit_after_discount = price_unit * (1 - discount / 100.0)
            tax_values = (
                tax_ids.compute_all(price_unit_after_discount, self.currency, quantity)
                if tax_ids
                else {
                    'total_excluded': price_unit * quantity,
                    'total_included': price_unit * quantity,
                }
            )
            return (0, 0, {
                'discount': discount,
                'id': randint(1, 1000000),
                'pack_lot_ids': [],
                'price_unit': price_unit,
                'product_id': product.id,
                'price_subtotal': tax_values['total_excluded'],
                'price_subtotal_incl': tax_values['total_included'],
                'qty': quantity,
                'tax_ids': [(6, 0, tax_ids.ids)]
            })

        def create_payment(payment_method, amount):
            return (0, 0, {
                'amount': amount,
                'name': fields.Datetime.now(),
                'payment_method_id': payment_method.id,
            })

        uid = uid or self.create_random_uid()

        # 1. generate the order lines
        order_lines = [
            create_order_line(product, quantity, discount and discount[0] or 0.0)
            for product, quantity, *discount
            in pos_order_lines_ui_args
        ]

        # 2. generate the payments
        total_amount_incl = sum(line[2]['price_subtotal_incl'] for line in order_lines)
        if payments is None:
            default_cash_pm = self.config.payment_method_ids.filtered(lambda pm: pm.is_cash_count)[:1]
            if not default_cash_pm:
                raise Exception('There should be a cash payment method set in the pos.config.')
            payments = [create_payment(default_cash_pm, total_amount_incl)]
        else:
            payments = [
                create_payment(pm, amount)
                for pm, amount in payments
            ]

        # 3. complete the fields of the order_data
        total_amount_base = sum(line[2]['price_subtotal'] for line in order_lines)
        return {
            'data': {
                'amount_paid': sum(payment[2]['amount'] for payment in payments),
                'amount_return': 0,
                'amount_tax': total_amount_incl - total_amount_base,
                'amount_total': total_amount_incl,
                'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
                'fiscal_position_id': fiscal_position.id,
                'pricelist_id': self.config.pricelist_id.id,
                'lines': order_lines,
                'name': 'Order %s' % uid,
                'partner_id': customer and customer.id,
                'pos_session_id': self.pos_session.id,
                'sequence_number': 2,
                'statement_ids': payments,
                'uid': uid,
                'user_id': self.env.user.id,
                'to_invoice': is_invoiced,
            },
            'id': uid,
            'to_invoice': is_invoiced,
        }

    @classmethod
    def create_product(cls, name, category, lst_price, standard_price=None, tax_ids=None, sale_account=None):
        product = cls.env['product.product'].create({
            'type': 'product',
            'available_in_pos': True,
            'taxes_id': [(5, 0, 0)] if not tax_ids else [(6, 0, tax_ids)],
            'name': name,
            'categ_id': category.id,
            'lst_price': lst_price,
            'standard_price': standard_price if standard_price else 0.0,
        })
        if sale_account:
            product.property_account_income_id = sale_account
        return product

    @classmethod
    def adjust_inventory(cls, products, quantities):
        """ Adjust inventory of the given products
        """
        for product, qty in zip(products, quantities):
            cls.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': qty,
                'location_id': cls.stock_location_components.id,
            }).action_apply_inventory()

    def open_new_session(self, opening_cash=0):
        """ Used to open new pos session in each configuration.

        - The idea is to properly set values that are constant
          and commonly used in an open pos session.
        - Calling this method is also a prerequisite for using
          `self.create_ui_order_data` function.

        Fields:
            * config : the pos.config currently being used.
                Its value is set at `self.setUp` of the inheriting
                test class.
            * pos_session : the current_session_id of config
            * currency : currency of the current pos.session
            * pricelist : the default pricelist of the session
        """
        self.config.open_session_cb(check_coa=False)
        self.pos_session = self.config.current_session_id
        self.currency = self.pos_session.currency_id
        self.pricelist = self.pos_session.config_id.pricelist_id
        self.pos_session.set_cashbox_pos(opening_cash, None)
        return self.pos_session

    def _run_test(self, args):
        pos_session = self._start_pos_session(args['payment_methods'], args.get('opening_cash', 0))
        _logger.info('DONE: Start session.')
        orders_map = self._create_orders(args['orders'])
        _logger.info('DONE: Orders created.')
        before_closing_cb = args.get('before_closing_cb')
        if before_closing_cb:
            before_closing_cb()
            _logger.info('DONE: Call of before_closing_cb.')
        self._check_invoice_journal_entries(pos_session, orders_map, expected_values=args['journal_entries_before_closing'])
        _logger.info('DONE: Checks for journal entries before closing the session.')
        total_cash_payment = sum(pos_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        pos_session.post_closing_cash_details(total_cash_payment)
        pos_session.close_session_from_ui()
        after_closing_cb = args.get('after_closing_cb')
        if after_closing_cb:
            after_closing_cb()
            _logger.info('DONE: Call of after_closing_cb.')
        self._check_session_journal_entries(pos_session, expected_values=args['journal_entries_after_closing'])
        _logger.info('DONE: Checks for journal entries after closing the session.')

    def _start_pos_session(self, payment_methods, opening_cash):
        self.config.write({'payment_method_ids': [(6, 0, payment_methods.ids)]})
        pos_session = self.open_new_session(opening_cash)
        self.assertEqual(self.config.payment_method_ids.ids, pos_session.payment_method_ids.ids, msg='Payment methods in the config should be the same as the session.')
        return pos_session

    def _create_orders(self, order_data_params):
        '''Returns a dict mapping uid to its created pos.order record.'''
        result = {}
        for params in order_data_params:
            order_data = self.create_ui_order_data(**params)
            result[params['uid']] = self.env['pos.order'].browse([order['id'] for order in self.env['pos.order'].create_from_ui([order_data])])
        return result

    def _check_invoice_journal_entries(self, pos_session, orders_map, expected_values):
        '''Checks the invoice, together with the payments, from each invoiced order.'''
        currency_rounding = pos_session.currency_id.rounding

        for uid in orders_map:
            order = orders_map[uid]
            if not order.is_invoiced:
                continue
            invoice = order.account_move
            # allow not checking the invoice since pos is not creating the invoices
            if expected_values[uid].get('invoice'):
                self._assert_account_move(invoice, expected_values[uid]['invoice'])
                _logger.info('DONE: Check of invoice for order %s.', uid)

            for pos_payment in order.payment_ids:
                if pos_payment.payment_method_id == self.pay_later_pm:
                    # Skip the pay later payments since there are no journal entries
                    # for them when invoicing.
                    continue

                # This predicate is used to match the pos_payment's journal entry to the
                # list of payments specified in the 'payments' field of the `_run_test`
                # args.
                def predicate(args):
                    payment_method, amount = args
                    first = payment_method == pos_payment.payment_method_id
                    second = tools.float_is_zero(pos_payment.amount - amount, precision_rounding=currency_rounding)
                    return first and second

                self._find_then_assert_values(pos_payment.account_move_id, expected_values[uid]['payments'], predicate)
                _logger.info('DONE: Check of invoice payment (%s, %s) for order %s.', pos_payment.payment_method_id.name, pos_payment.amount, uid)

    def _check_session_journal_entries(self, pos_session, expected_values):
        '''Checks the journal entries after closing the session excluding entries checked in `_check_invoice_journal_entries`.'''
        currency_rounding = pos_session.currency_id.rounding

        # check expected session journal entry
        self._assert_account_move(pos_session.move_id, expected_values['session_journal_entry'])
        _logger.info("DONE: Check of the session's account move.")

        # check expected cash journal entries
        for statement_line in pos_session.cash_register_id.line_ids:
            def statement_line_predicate(args):
                return tools.float_is_zero(statement_line.amount - args[0], precision_rounding=currency_rounding)
            self._find_then_assert_values(statement_line.move_id, expected_values['cash_statement'], statement_line_predicate)
        _logger.info("DONE: Check of cash statement lines.")

        # check expected bank payments
        for bank_payment in pos_session.bank_payment_ids:
            def bank_payment_predicate(args):
                return tools.float_is_zero(bank_payment.amount - args[0], precision_rounding=currency_rounding)
            self._find_then_assert_values(bank_payment.move_id, expected_values['bank_payments'], bank_payment_predicate)
        _logger.info("DONE: Check of bank account payments.")

    def _find_then_assert_values(self, account_move, source_of_expected_vals, predicate):
        expected_move_vals = next(move_vals for args, move_vals in source_of_expected_vals if predicate(args))
        self._assert_account_move(account_move, expected_move_vals)

    def _assert_account_move(self, account_move, expected_account_move_vals):
        if expected_account_move_vals:
            # We allow partial checks of the lines of the account move if `line_ids_predicate` is specified.
            # This means that only those that satisfy the predicate are compared to the expected account move line_ids.
            line_ids_predicate = expected_account_move_vals.pop('line_ids_predicate', lambda _: True)
            self.assertRecordValues(account_move.line_ids.filtered(line_ids_predicate), expected_account_move_vals.pop('line_ids'))
            self.assertRecordValues(account_move, [expected_account_move_vals])
        else:
            # if the expected_account_move_vals is falsy, the account_move should be falsy.
            self.assertFalse(account_move)
