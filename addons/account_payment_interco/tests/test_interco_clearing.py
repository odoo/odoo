from datetime import date
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools.misc import format_date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestIntercoClearing(AccountTestInvoicingCommon):

    def _check_accounting_installed(self, expected=True):
        if ('accountant' in self.env['ir.module.module']._installed()) != expected:
            self.skipTest(f"`accountant` is {'not ' if expected else ''}installed.")

    @classmethod
    def _setup_outstanding_account(cls, active=True, direction='inbound'):
        pml = cls.inbound_payment_method_line if direction == 'inbound' else cls.outbound_payment_method_line
        if not active:
            pml.payment_account_id = False
        else:
            account_payment_method = cls.env['account.payment.method'].sudo().create({
               'name': 'Test Payment Method',
               'code': 'test_payment_method',
               'payment_type': direction,
            })
            pml.payment_method_id = account_payment_method
            pml.payment_provider_id = cls.payment_provider_be

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('generic_coa')
    def setUpClass(cls):
        super().setUpClass()

        cls.amount = 100.0
        kenya, shelling, cls.usd = (cls.env.ref(f'base.{x}') for x in ('ke', 'KES', 'USD'))
        cls.frozen_date = date(2019, 6, 1)
        cls.frozen_datestr = format_date(env=cls.env, value=cls.frozen_date, date_format='short')
        cls.startClassPatcher(freeze_time(cls.frozen_datestr, tick=True))

        cls.kenyian_partner_name = 'Ndovu Holdings'
        cls.kenyian_partner = cls.env['res.partner'].create({
            'name': cls.kenyian_partner_name,
            'country_id': kenya.id,
            'vat': 'P000607371B',
            'is_company': True,
            'supplier_rank': 1,
        })
        cls.company_ke = cls.setup_other_company(
            name='Odoo KE LTD',
            vat='P052112956W',
            currency_id=shelling.id,
        )['company']

        companies_data = (
            (cls.company_ke, cls.usd, 0.0073),
            (cls.env.company, shelling, 136.9863),
        )
        account_data = (
            ('c/c interco receivable Odoo', '210002', 'asset_receivable'),
            ('c/c interco payable Odoo', '489286', 'liability_payable'),
        )
        for company, currency, rate in companies_data:
            company.account_interco_clearing_journal_id = cls.env['account.journal'].create({
                'name': 'Intercompany clearings',
                'type': 'general',
                'company_id': company.id,
            })
            cls.env['res.currency.rate'].create({
                'name': fields.Date.today(),
                'rate': rate,
                'currency_id': currency.id,
                'company_id': company.id,
            })
            for account_name, account_code, account_type in account_data:
                account = cls.env['account.account'].with_company(company).create({
                    'name': f'{account_name} {company.country_id.code}',
                    'code': account_code,
                    'account_type': account_type,
                    'reconcile': True,
                })
                if account_type == 'asset_receivable':
                    company.account_interco_receivable_id = account
                else:
                    company.account_interco_payable_id = account

        cls.payment_method_be = cls.env.ref('payment.payment_method_unknown').copy()
        cls.payment_provider_be = cls.env['payment.provider'].create({
            'name': 'Dummy Provider BE',
            'code': 'none',
            'state': 'test',
            'is_published': True,
            'payment_method_ids': [Command.set([cls.payment_method_be.id])],
        })
        cls.payment_method_be.write({'active': True})

    def _create_payment(self, order, direction='inbound', extra_transaction_data=None):
        payment_amount = self.company_ke.currency_id._convert(
            order.amount_total,
            self.env.company.currency_id,
            self.company_ke,
            fields.Date.today(),
        )
        self.payment_be = self.env['account.payment'].create({
            'memo': order.name,
            'amount': payment_amount,
            'payment_type': 'inbound',
            'currency_id': self.usd.id,
            'partner_id': self.kenyian_partner.id,
            'partner_type': 'customer' if direction == 'inbound' else 'supplier',
            'journal_id': self.payment_provider_be.journal_id.id,
            'company_id': self.payment_provider_be.company_id.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        self.payment_transaction_be = self.env['payment.transaction'].create({
            'payment_id': self.payment_be.id,
            'provider_id': self.payment_provider_be.id,
            'payment_method_id': self.payment_method_be.id,
            'operation': 'online_direct',
            'partner_id': self.kenyian_partner.id,
            'amount': order.amount_total,
            'currency_id': self.usd.id,
            **extra_transaction_data,
        })

    def _verify_asserts(self, order, move, account, sign):
        company = move.company_id
        base_amount = self.payment_be.currency_id._convert(self.payment_be.amount, company.currency_id, company, move.date)

        self.assertEqual(move.payment_state, 'paid')
        move_line = move.line_ids.filtered(lambda l: l.account_type in ('asset_receivable', 'liability_payable'))
        self.assertTrue(move_line.reconciled)

        clearing_entry = self.env['account.move'].search([
            ('ref', '=ilike', f'%{self.payment_be.memo}'),
            ('company_id', '=', self.company_ke.id),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
        ])
        self.assertTrue(clearing_entry)
        clearing_line = clearing_entry.line_ids.filtered(lambda l: l.account_id == move_line.account_id)
        self.assertTrue(clearing_line.reconciled)

        entry = self.env['account.move'].search([
            ('company_id', '=', self.company_ke.id),
            ('ref', '=ilike', f'Interco Settlement - {order.name}'),
            ('move_type', '=', 'entry'),
        ])
        self.assertTrue(entry)
        self.assertEqual(entry.state, 'posted')

        lbl = f'{self.kenyian_partner_name} / {move.name}'
        move_line = move.line_ids.filtered(lambda l: l.account_type in ('asset_receivable', 'liability_payable'))[:1]
        self.assertRecordValues(entry.line_ids, [{
            'name': lbl,
            'account_id': account.id,
            'balance': sign * base_amount,
            'reconciled': False
        }, {
            'name': lbl,
            'account_id': move_line.account_id.id,
            'balance': -sign * base_amount,
            'reconciled': True,
        }])

        self.assertTrue(self.payment_be.move_id)
        payment_line = self.payment_be.move_id.line_ids.filtered(
            lambda line: line.account_id == self.payment_be.destination_account_id
        )
        self.assertRecordValues(payment_line, [{'reconciled': True, 'amount_residual': 0.0}])


@tagged('post_install', '-at_install')
class TestIntercoClearingSale(TestIntercoClearing):

    def test_interco_sale(self):
        self.ensure_installed('sale')

        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', True)
        self.sale_order_ke = self.env['sale.order'].with_company(self.company_ke).sudo().create({
            'company_id': self.company_ke.id,
            'partner_id': self.kenyian_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': product_qty,
                    'price_unit': price_unit,
                    'currency_id': self.usd.id,
                }) for (product, product_qty, price_unit) in [
                    (self.product_a, 2, 40.0),
                    (self.product_b, 1, 20.0),
                ]
            ],
        })

        for (accounting_installed, outstanding_accounts) in ((True, True), (False, True)):
            with self.subTest(accounting_installed=accounting_installed, active=outstanding_accounts):
                self._check_accounting_installed(expected=accounting_installed)
                self._setup_outstanding_account(active=outstanding_accounts, direction='inbound')

                sale_order_ke = self.sale_order_ke.with_company(self.company_ke)
                sale_order_ke.sudo().action_confirm()

                self._create_payment(sale_order_ke, 'inbound', {
                    'sale_order_ids': [Command.set(self.sale_order_ke.ids)],
                })
                self.payment_be.action_post()
                self.payment_transaction_be.sudo()._set_done()
                self.payment_transaction_be.sudo()._post_process()
                self._verify_asserts(self.sale_order_ke, self.sale_order_ke.invoice_ids, self.company_ke.account_interco_receivable_id, 1)


@tagged('post_install', '-at_install')
class TestIntercoClearingPurchase(TestIntercoClearing):

    def test_interco_purchase(self):
        self.ensure_installed('purchase')

        (self.product_a + self.product_b).purchase_method = 'purchase'
        self.purchase_order_ke = self.env['purchase.order'].with_company(self.company_ke).sudo().create({
            'partner_id': self.kenyian_partner.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                    'product_qty': product_qty,
                    'price_unit': price_unit,
                    'currency_id': self.usd.id,
                }) for (product, product_qty, price_unit) in [
                    (self.product_a, 2, 40.0),
                    (self.product_b, 1, 20.0),
                ]
            ],
        })

        for (accounting_installed, outstanding_accounts) in ((True, True), (False, True)):
            with self.subTest(accounting_installed=accounting_installed, active=outstanding_accounts):
                self._check_accounting_installed(expected=accounting_installed)
                self._setup_outstanding_account(active=outstanding_accounts, direction='outbound')

                purchase_order_ke = self.purchase_order_ke.with_company(self.company_ke)
                purchase_order_ke.sudo().button_confirm()

                bill_data = purchase_order_ke.action_create_invoice()
                self.bill = self.env['account.move'].browse(bill_data['res_id'])
                self.bill.invoice_date = fields.Date.today()

                self._create_payment(purchase_order_ke, 'outbound', {
                    'invoice_ids': [Command.set(self.bill.ids)],
                })
                self.payment_be.action_post()
                self.payment_transaction_be.sudo()._set_done()
                self.payment_transaction_be.sudo()._post_process()
                self._verify_asserts(self.purchase_order_ke, self.bill, self.company_ke.account_interco_payable_id, -1)
