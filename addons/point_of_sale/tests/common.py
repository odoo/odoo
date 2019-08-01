# -*- coding: utf-8 -*-
from odoo.tests import common


class TestPointOfSaleCommon(common.TransactionCase):

    def setUp(self):
        super(TestPointOfSaleCommon, self).setUp()
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementLine = self.env['account.bank.statement.line']
        self.PosMakePayment = self.env['pos.make.payment']
        self.PosOrder = self.env['pos.order']
        self.PosSession = self.env['pos.session']
        company = self.env.ref('base.main_company')
        self.company_id = company.id
        coa = self.env['account.chart.template'].search([
            ('currency_id', '=', company.currency_id.id),
            ], limit=1)
        test_sale_journal = self.env['account.journal'].create({'name': 'Sales Journal - Test',
                                                'code': 'TSJ',
                                                'type': 'sale',
                                                'company_id': self.company_id})
        company.write({'anglo_saxon_accounting': coa.use_anglo_saxon,
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
            'journal_ids': [(0, 0, {'name': 'Cash Journal - Test',
                                                       'code': 'TSC',
                                                       'type': 'cash',
                                                       'company_id': self.company_id,
                                                       'journal_user': True})],
            })
        self.led_lamp = self.env.ref('point_of_sale.led_lamp')
        self.whiteboard_pen = self.env.ref('point_of_sale.whiteboard_pen')
        self.newspaper_rack = self.env.ref('point_of_sale.newspaper_rack')

        # create a new session
        self.pos_order_session0 = self.env['pos.session'].create({
            'user_id': 1,
            'config_id': self.pos_config.id
        })

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
