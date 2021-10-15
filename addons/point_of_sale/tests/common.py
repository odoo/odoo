# -*- coding: utf-8 -*-
from random import randint
from datetime import datetime

from odoo import fields, tools
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests.common import SavepointCase, Form
from odoo.tests import tagged


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
            'is_cash_count': True,
            'cash_journal_id': cls.company_data['default_journal_cash'].id,
            'company_id': cls.env.company.id,
        })
        cls.bank_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'is_cash_count': False,
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
            'type': 'sale',
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
        })

        # Set basic defaults
        cls.company = cls.company_data['company']
        cls.pos_sale_journal = cls.env['account.journal'].create({
            'type': 'sale',
            'name': 'Point of Sale Test',
            'code': 'POST',
            'company_id': cls.company.id,
            'sequence': 20
        })
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
        cls.customer = cls.env['res.partner'].create({'name': 'Test Customer'})
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
        cash_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Cash',
            'receivable_account_id': cls.pos_receivable_account.id,
            'is_cash_count': True,
            'cash_journal_id': cls.company_data['default_journal_cash'].id,
            'company_id': cls.env.company.id,
        })
        bank_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'receivable_account_id': cls.pos_receivable_account.id,
            'is_cash_count': False,
            'company_id': cls.env.company.id,
        })
        cash_split_pm = cls.env['pos.payment.method'].create({
            'name': 'Split (Cash) PM',
            'receivable_account_id': cls.pos_receivable_account.id,
            'split_transactions': True,
            'is_cash_count': True,
            'cash_journal_id': cls.company_data['default_journal_cash'].id,
        })
        bank_split_pm = cls.env['pos.payment.method'].create({
            'name': 'Split (Bank) PM',
            'receivable_account_id': cls.pos_receivable_account.id,
            'split_transactions': True,
        })
        config.write({'payment_method_ids': [(4, cash_split_pm.id), (4, bank_split_pm.id), (4, cash_payment_method.id), (4, bank_payment_method.id)]})
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
        other_pricelist = cls.env['product.pricelist'].create({
            'name': 'Public Pricelist Other',
            'currency_id': cls.other_currency.id,
        })
        other_cash_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Cash Other',
            'receivable_account_id': cls.pos_receivable_account.id,
            'is_cash_count': True,
            'cash_journal_id': other_cash_journal.id,
        })
        other_bank_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Bank Other',
            'receivable_account_id': cls.pos_receivable_account.id,
        })

        new_config = Form(cls.env['pos.config'])
        new_config.name = 'Shop Other'
        new_config.invoice_journal_id = other_invoice_journal
        new_config.journal_id = other_sales_journal
        new_config.use_pricelist = True
        new_config.available_pricelist_ids.clear()
        new_config.available_pricelist_ids.add(other_pricelist)
        new_config.pricelist_id = other_pricelist
        new_config.payment_method_ids.clear()
        new_config.payment_method_ids.add(other_cash_payment_method)
        new_config.payment_method_ids.add(other_bank_payment_method)
        config = new_config.save()
        return config

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
        """
        tax7 = cls.env['account.tax'].create({'name': 'Tax 7%', 'amount': 7})
        tax10 = cls.env['account.tax'].create({'name': 'Tax 10%', 'amount': 10, 'price_include': True, 'include_base_amount': False})
        (tax7 | tax10).mapped('invoice_repartition_line_ids').write({'account_id': cls.tax_received_account.id})
        (tax7 | tax10).mapped('refund_repartition_line_ids').write({'account_id': cls.tax_received_account.id})

        tax_group_7_10 = tax7.copy()
        with Form(tax_group_7_10) as tax:
            tax.name = 'Tax 7+10%'
            tax.amount_type = 'group'
            tax.children_tax_ids.add(tax7)
            tax.children_tax_ids.add(tax10)

        return {
            'tax7': tax7,
            'tax10': tax10,
            'tax_group_7_10': tax_group_7_10
        }

    ####################
    ## public methods ##
    ####################

    def create_random_uid(self):
        return ('%05d-%03d-%04d' % (randint(1, 99999), randint(1, 999), randint(1, 9999)))

    def create_ui_order_data(self, product_quantity_pairs, customer=False, is_invoiced=False, payments=None, uid=None):
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

        :param list(tuple) product_quantity_pairs: pair of `ordered product` and `quantity`
        :param list(tuple) payments: pair of `payment_method` and `amount`
        """
        default_fiscal_position = self.config.default_fiscal_position_id
        fiscal_position = customer.property_account_position_id if customer else default_fiscal_position

        def create_order_line(product, quantity):
            price_unit = self.pricelist.get_product_price(product, quantity, False)
            tax_ids = fiscal_position.map_tax(product.taxes_id)
            tax_values = (
                tax_ids.compute_all(price_unit, self.currency, quantity)
                if tax_ids
                else {
                    'total_excluded': price_unit * quantity,
                    'total_included': price_unit * quantity,
                }
            )
            return (0, 0, {
                'discount': 0,
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
        order_lines = [create_order_line(product, quantity) for product, quantity in product_quantity_pairs]

        # 2. generate the payments
        total_amount_incl = sum(line[2]['price_subtotal_incl'] for line in order_lines)
        if payments is None:
            payments = [create_payment(self.cash_pm, total_amount_incl)]
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
        inventory = cls.env['stock.inventory'].create({
            'name': 'Inventory adjustment'
        })
        for product, qty in zip(products, quantities):
            cls.env['stock.inventory.line'].create({
                'product_id': product.id,
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'inventory_id': inventory.id,
                'product_qty': qty,
                'location_id': cls.stock_location_components.id,
            })
        inventory._action_start()
        inventory.action_validate()

    def open_new_session(self):
        """ Used to open new pos session in each configuration.

        - The idea is to properly set values that are constant
          and commonly used in an open pos session.
        - Calling this method is also a prerequisite for using
          `self.create_ui_order_data` function.

        Fields:
            * config : the pos.config currently being used.
                Its value is set at `self.setUp` of the inheriting
                test class.
            * session : the current_session_id of config
            * currency : currency of the current pos.session
            * pricelist : the default pricelist of the session
            * cash_pm : cash payment method of the session
            * bank_pm : bank payment method of the session
            * cash_split_pm : credit payment method of the session
            * bank_split_pm : split bank payment method of the session
        """
        self.config.open_session_cb(check_coa=False)
        self.pos_session = self.config.current_session_id
        self.currency = self.pos_session.currency_id
        self.pricelist = self.pos_session.config_id.pricelist_id
        self.cash_pm = self.pos_session.payment_method_ids.filtered(lambda pm: pm.is_cash_count and not pm.split_transactions)[:1]
        self.bank_pm = self.pos_session.payment_method_ids.filtered(lambda pm: not pm.is_cash_count and not pm.split_transactions)[:1]
        self.cash_split_pm = self.pos_session.payment_method_ids.filtered(lambda pm: pm.is_cash_count and pm.split_transactions)[:1]
        self.bank_split_pm = self.pos_session.payment_method_ids.filtered(lambda pm: not pm.is_cash_count and pm.split_transactions)[:1]
