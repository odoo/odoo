# -*- coding: utf-8 -*-
from random import randint

from odoo import fields
from odoo.tests.common import TransactionCase, Form
from odoo.tools import float_is_zero


class TestPointOfSaleCommon(TransactionCase):

    def setUp(self):
        super(TestPointOfSaleCommon, self).setUp()
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementLine = self.env['account.bank.statement.line']
        self.PosMakePayment = self.env['pos.make.payment']
        self.PosOrder = self.env['pos.order']
        self.PosSession = self.env['pos.session']
        self.company = self.env.ref('base.main_company')
        self.company_id = self.company.id
        coa = self.env['account.chart.template'].search([
            ('currency_id', '=', self.company.currency_id.id),
            ], limit=1)
        test_sale_journal = self.env['account.journal'].create({'name': 'Sales Journal - Test',
                                                'code': 'TSJ',
                                                'type': 'sale',
                                                'company_id': self.company_id})
        self.company.write({'anglo_saxon_accounting': coa.use_anglo_saxon,
            'bank_account_code_prefix': coa.bank_account_code_prefix,
            'cash_account_code_prefix': coa.cash_account_code_prefix,
            'transfer_account_code_prefix': coa.transfer_account_code_prefix,
            'chart_template_id': coa.id,
        })
        self.product3 = self.env.ref('product.product_product_3')
        self.product4 = self.env.ref('product.product_product_4')
        self.partner1 = self.env.ref('base.res_partner_1')
        self.partner4 = self.env.ref('base.res_partner_4')
        self.pos_config = self.env.ref('point_of_sale.pos_config_main')
        self.pos_config.write({
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
        })
        self.led_lamp = self.env.ref('point_of_sale.led_lamp')
        self.whiteboard_pen = self.env.ref('point_of_sale.whiteboard_pen')
        self.newspaper_rack = self.env.ref('point_of_sale.newspaper_rack')

        self.cash_payment_method = self.pos_config.payment_method_ids.filtered(lambda pm: pm.name == 'Cash')
        self.bank_payment_method = self.pos_config.payment_method_ids.filtered(lambda pm: pm.name == 'Bank')
        self.credit_payment_method = self.env['pos.payment.method'].create({
            'name': 'Credit',
            'receivable_account_id': self.company.account_default_pos_receivable_account_id.id,
            'split_transactions': True,
        })
        self.pos_config.write({'payment_method_ids': [(4, self.credit_payment_method.id)]})

        # create a VAT tax of 10%, included in the public price
        Tax = self.env['account.tax']
        account_tax_10_incl = Tax.create({
            'name': 'VAT 10 perc Incl',
            'amount_type': 'percent',
            'amount': 10.0,
            'price_include': 1
        })

        # assign this 10 percent tax on the [PCSC234] PC Assemble SC234 product
        # as a sale tax
        self.product3.taxes_id = [(6, 0, [account_tax_10_incl.id])]

        # create a VAT tax of 5%, which is added to the public price
        account_tax_05_incl = Tax.create({
            'name': 'VAT 5 perc Incl',
            'amount_type': 'percent',
            'amount': 5.0,
            'price_include': 0
        })

        # create a second VAT tax of 5% but this time for a child company, to
        # ensure that only product taxes of the current session's company are considered
        #(this tax should be ignore when computing order's taxes in following tests)
        account_tax_05_incl_chicago = Tax.with_context(default_company_id=self.ref('stock.res_company_1')).create({
            'name': 'VAT 05 perc Excl (US)',
            'amount_type': 'percent',
            'amount': 5.0,
            'price_include': 0,
        })

        self.product4.company_id = False
        # I assign those 5 percent taxes on the PCSC349 product as a sale taxes
        self.product4.write(
            {'taxes_id': [(6, 0, [account_tax_05_incl.id, account_tax_05_incl_chicago.id])]})

        # Set account_id in the generated repartition lines. Automatically, nothing is set.
        invoice_rep_lines = (account_tax_05_incl | account_tax_05_incl_chicago | account_tax_10_incl).mapped('invoice_repartition_line_ids')
        refund_rep_lines = (account_tax_05_incl | account_tax_05_incl_chicago | account_tax_10_incl).mapped('refund_repartition_line_ids')

        tax_received_account = self.company.account_sale_tax_id.mapped('invoice_repartition_line_ids.account_id')
        (invoice_rep_lines | refund_rep_lines).write({'account_id': tax_received_account.id})


class TestPoSCommon(TransactionCase):
    """ Set common values for different special test cases.

    The idea is to set up common values here for the tests
    and implement different special scenarios by inheriting
    this class.
    """

    def setUp(self):
        super(TestPoSCommon, self).setUp()

        self.pos_manager = self.env.ref('base.user_admin')
        self.env = self.env(user=self.pos_manager)

        # Set basic defaults
        self.company = self.env.ref('base.main_company')
        self.pos_sale_journal = self.env['account.journal'].create({
            'type': 'sale',
            'name': 'Point of Sale Test',
            'code': 'POST',
            'company_id': self.company.id,
            'sequence': 20
        })
        self.invoice_journal = self.env['account.journal'].create({
            'type': 'sale',
            'name': 'Invoice Journal Test',
            'code': 'INVT',
            'company_id': self.company.id,
            'sequence': 21
        })
        self.receivable_account = self.pos_manager.partner_id.property_account_receivable_id
        self.tax_received_account = self.company.account_sale_tax_id.mapped('invoice_repartition_line_ids.account_id')
        self.pos_receivable_account = self.company.account_default_pos_receivable_account_id
        self.other_receivable_account = self.env['account.account'].create({
            'name': 'Other Receivable',
            'code': 'RCV00' ,
            'user_type_id': self.env['account.account.type'].create({'name': 'RCV type', 'type': 'receivable', 'internal_group': 'asset'}).id,
            'internal_group': 'asset',
            'reconcile': True,
        })

        # company_currency can be different from `base.USD` depending on the localization installed
        self.company_currency = self.company.currency_id
        # other_currency is a currency different from the company_currency
        # sometimes company_currency is different from USD, so handle appropriately.
        self.other_currency = self.env.ref('base.EUR') if self.company_currency == self.env.ref('base.USD') else self.env.ref('base.USD')

        self.currency_pricelist = self.env['product.pricelist'].create({
            'name': 'Public Pricelist',
            'currency_id': self.company_currency.id,
        })
        # Set Point of Sale configurations
        # basic_config
        #   - derived from 'point_of_sale.pos_config_main' with added invoice_journal_id and credit payment method.
        # other_currency_config
        #   - pos.config set to have currency different from company currency.
        self.basic_config = self._create_basic_config()
        self.other_currency_config = self._create_other_currency_config()

        # Set product categories
        # categ_basic
        #   - just the plain 'product.product_category_all'
        # categ_anglo
        #   - product category with fifo and real_time valuations
        #   - used for checking anglo saxon accounting behavior
        self.categ_basic = self.env.ref('product.product_category_all')
        self.categ_anglo = self._create_categ_anglo()

        # other basics
        self.sale_account = self.categ_basic.property_account_income_categ_id
        self.other_sale_account = self.env['account.account'].search([
            ('company_id', '=', self.company.id),
            ('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id),
            ('id', '!=', self.sale_account.id)
        ], limit=1)

        # Set customers
        self.customer = self.env['res.partner'].create({'name': 'Test Customer'})
        self.other_customer = self.env['res.partner'].create({'name': 'Other Customer', 'property_account_receivable_id': self.other_receivable_account.id})

        # Set taxes
        # self.taxes => dict
        #   keys: 'tax7', 'tax10'(price_include=True), 'tax_group_7_10'
        self.taxes = self._create_taxes()

    #####################
    ## private methods ##
    #####################

    def _create_basic_config(self):
        new_config = Form(self.env['pos.config'])
        new_config.name = 'PoS Shop Test'
        new_config.module_account = True
        new_config.invoice_journal_id = self.invoice_journal
        new_config.journal_id = self.pos_sale_journal
        new_config.available_pricelist_ids.clear()
        new_config.available_pricelist_ids.add(self.currency_pricelist)
        new_config.pricelist_id = self.currency_pricelist
        config = new_config.save()
        cash_journal = config.payment_method_ids.filtered(lambda pm: pm.is_cash_count)[:1].cash_journal_id
        cash_split_pm = self.env['pos.payment.method'].create({
            'name': 'Split (Cash) PM',
            'receivable_account_id': self.pos_receivable_account.id,
            'split_transactions': True,
            'is_cash_count': True,
            'cash_journal_id': cash_journal.id,
        })
        config.write({'payment_method_ids': [(4,cash_split_pm.id,0)]})
        return config

    def _create_other_currency_config(self):
        (self.other_currency.rate_ids | self.company_currency.rate_ids).unlink()
        self.env['res.currency.rate'].create({
            'rate': 0.5,
            'currency_id': self.other_currency.id,
        })
        other_cash_journal = self.env['account.journal'].create({
            'name': 'Cash Other',
            'type': 'cash',
            'company_id': self.company.id,
            'code': 'CSHO',
            'sequence': 10,
            'currency_id': self.other_currency.id
        })
        other_invoice_journal = self.env['account.journal'].create({
            'name': 'Customer Invoice Other',
            'type': 'sale',
            'company_id': self.company.id,
            'code': 'INVO',
            'sequence': 11,
            'currency_id': self.other_currency.id
        })
        other_sales_journal = self.env['account.journal'].create({
            'name':'PoS Sale Other',
            'type': 'sale',
            'code': 'POSO',
            'company_id': self.company.id,
            'sequence': 12,
            'currency_id': self.other_currency.id
        })
        other_pricelist = self.env['product.pricelist'].create({
            'name': 'Public Pricelist Other',
            'currency_id': self.other_currency.id,
        })
        other_cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'Cash Other',
            'receivable_account_id': self.pos_receivable_account.id,
            'is_cash_count': True,
            'cash_journal_id': other_cash_journal.id,
        })
        other_bank_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bank Other',
            'receivable_account_id': self.pos_receivable_account.id,
        })

        new_config = Form(self.env['pos.config'])
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

    def _create_categ_anglo(self):
        return self.env['product.category'].create({
            'name': 'Anglo',
            'parent_id': False,
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

    def _create_taxes(self):
        """ Create taxes

        tax7: 7%, excluded in product price
        tax10: 10%, included in product price
        """
        tax7 = self.env['account.tax'].create({'name': 'Tax 7%', 'amount': 7})
        tax10 = self.env['account.tax'].create({'name': 'Tax 10%', 'amount': 10, 'price_include': True, 'include_base_amount': False})
        (tax7 | tax10).mapped('invoice_repartition_line_ids').write({'account_id': self.tax_received_account.id})
        (tax7 | tax10).mapped('refund_repartition_line_ids').write({'account_id': self.tax_received_account.id})

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
            tax_ids = fiscal_position.map_tax(product.taxes_id) if fiscal_position else product.taxes_id
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
                'user_id': self.pos_manager.id,
                'to_invoice': is_invoiced,
            },
            'id': uid,
            'to_invoice': is_invoiced,
        }

    def create_product(self, name, category, lst_price, standard_price=None, tax_ids=None, sale_account=None):
        product = self.env['product.product'].create({
            'type': 'product',
            'available_in_pos': True,
            'taxes_id': [(5, 0, 0)] if not tax_ids else [(6, 0, tax_ids)],
            'name': name,
            'categ_id': category.id,
            'lst_price': lst_price,
            'standard_price': standard_price if standard_price else 0.0,
        })
        product.invoice_policy = 'delivery'
        if sale_account:
            product.property_account_income_id = sale_account
        return product

    def adjust_inventory(self, products, quantities):
        """ Adjust inventory of the given products
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory adjustment'
        })
        for product, qty in zip(products, quantities):
            self.env['stock.inventory.line'].create({
                'product_id': product.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'inventory_id': inventory.id,
                'product_qty': qty,
                'location_id': self.env.ref('stock.stock_location_components').id,
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
        """
        self.config.open_session_cb()
        self.pos_session = self.config.current_session_id
        self.currency = self.pos_session.currency_id
        self.pricelist = self.pos_session.config_id.pricelist_id
        self.cash_pm = self.pos_session.payment_method_ids.filtered(lambda pm: pm.is_cash_count and not pm.split_transactions)[:1]
        self.bank_pm = self.pos_session.payment_method_ids.filtered(lambda pm: not pm.is_cash_count and not pm.split_transactions)[:1]
        self.cash_split_pm = self.pos_session.payment_method_ids.filtered(lambda pm: pm.is_cash_count and pm.split_transactions)[:1]
