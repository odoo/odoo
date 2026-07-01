from datetime import date
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import format_date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestIntercoClearing(AccountTestInvoicingCommon):

    @classmethod
    def _kenyian(cls, obj_or_name):
        target = cls.env[obj_or_name] if isinstance(obj_or_name, str) else obj_or_name
        return target.with_company(cls.company_ke)

    @classmethod
    def _create_interco_journal(cls, company):
        return cls.env['account.journal'].create({
            'name': 'Intercompany clearings',
            'type': 'general',
            'company_id': company.id,
        })

    @classmethod
    def _setup_outstanding_account(cls, active=True):
        if not active:
            cls.inbound_payment_method_line.payment_account_id = False
        else:
            account_payment_method = cls.env['account.payment.method'].sudo().create({
               'name': 'Test Payment Method',
               'code': 'test_payment_method',
               'payment_type': 'inbound',
            })
            cls.inbound_payment_method_line.payment_method_id = account_payment_method
            cls.inbound_payment_method_line.payment_provider_id = cls.payment_provider_be

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('generic_coa')
    def setUpClass(cls):
        super().setUpClass()

        cls.startClassPatcher(freeze_time('2019-06-01', tick=True))
        cls.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', True)

        # Master data lookup -------------------------------
        kenya, shelling, usd = (cls.env.ref(f'base.{x}') for x in ('ke', 'KES', 'USD'))

        # Partner
        cls.kenyian_partner = cls.env['res.partner'].create({
            'name': 'Ndovu Holdings',
            'country_id': kenya.id,
            'vat': 'P000607371B',
        })

        # Sale Order in Belgium -------------------------------
        cls.amount = 50.0
        cls.sale_order_be = cls.env['sale.order'].sudo().create({
            'partner_id': cls.kenyian_partner.id,
            'order_line': [Command.create({
                'product_id': cls.product_a.id,
                'product_uom_qty': 1,
                'price_unit': cls.amount,
                'currency_id': usd.id,
            })],
        })

        cls.payment_method_be = cls.env.ref('payment.payment_method_unknown').copy()
        cls.payment_provider_be = cls.env['payment.provider'].create({
            'name': 'Dummy Provider BE',
            'code': 'none',
            'state': 'test',
            'is_published': True,
            'payment_method_ids': [Command.set([cls.payment_method_be.id])],
        })
        cls.payment_method_be.write({'active': True})

        # Kenya ----------------------------------------------
        cls.company_ke = cls.setup_other_company(
            name='Odoo KE LTD',
            vat='P052112956W',
            currency_id=shelling.id,
        )['company']
        cls.company_ke.account_interco_clearing_journal_id = cls._create_interco_journal(cls.company_ke)
        cls.env.company.account_interco_clearing_journal_id = cls._create_interco_journal(cls.env.company)

        # Accounts -------------------------------------------
        cls.company_ke.account_interco_receivable_id = cls._kenyian('account.account').create({
            'name': 'c/c interco Odoo BE',
            'code': '210001',
            'account_type': 'asset_receivable',
            'reconcile': True,
        })
        cls.env.company.account_interco_payable_id = cls.env['account.account'].create({
            'name': 'c/c interco Odoo KE',
            'code': '489285',
            'account_type': 'liability_payable',
            'reconcile': True,
        })

    def _check_accounting_installed(self, expected=True):
        if ('accountant' in self.env['ir.module.module']._installed()) != expected:
            self.skipTest(f"`accountant` is {'not ' if expected else ''}installed.")

    def _check_interco_move(self):
        be_interco_entry = self.env['account.move'].search([
            ('company_id', '=', self.company_ke.id),
            ('ref', '=ilike', f'Interco Settlement - {self.sale_order_be.name}'),
            ('move_type', '=', 'entry'),
        ])
        self.assertTrue(be_interco_entry)
        self.assertEqual(be_interco_entry.state, 'posted')

        invoice = self.sale_order_be.invoice_ids
        other_base_amount = self.payment_be.currency_id._convert(
            self.payment_be.amount,
            invoice.company_id.currency_id,
            invoice.company_id,
            invoice.date,
        )
        datestr = format_date(env=self.env, value=date(2019, 6, 1), date_format='short')
        self.assertRecordValues(be_interco_entry.line_ids, [
            {
                'name': f'{datestr} / Ndovu Holdings / INV/2019/00001',
                'account_id': self.company_ke.account_interco_receivable_id.id,
                'balance': other_base_amount,
                'reconciled': False,
                'amount_residual': other_base_amount,
            },
            {
                'name': f'{datestr} / Ndovu Holdings / INV/2019/00001',
                'account_id': self._kenyian(self.kenyian_partner).property_account_receivable_id.id,
                'balance': -other_base_amount,
                'reconciled': True,
                'amount_residual': 0.0,
            }
        ])

    def _check_payment_move_reconciled(self):
        payment_receivable_line = self.payment_be.move_id.line_ids.filtered(
            lambda line: line.account_id == self.payment_be.destination_account_id
        )
        self.assertRecordValues(payment_receivable_line, [{'reconciled': True, 'amount_residual': 0.0}])

    def _check_payment_and_invoice(self):
        """ Test that posting the payment in BE automatically reconciles the payment entries. """
        # Check the payment state
        invoice = self.sale_order_be.invoice_ids
        self.assertEqual(invoice.payment_state, 'paid')

        # Check the Kenyan invoice
        invoice_ar_line = invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
        self.assertRecordValues(invoice_ar_line, [{
            'reconciled': True,
            'amount_residual': 0.0,
            'amount_residual_currency': 0.0,
        }])

        # Check the new Kenyan clearing entry
        ke_clearing_entry = self.env['account.move'].sudo().search([
            ('ref', '=ilike', f'%{self.payment_be.memo}'),
            ('company_id', '=', self.company_ke.id),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
        ])
        self.assertTrue(ke_clearing_entry)
        entry_receivable_line = ke_clearing_entry.line_ids.filtered(
            lambda line: line.account_id == invoice_ar_line.account_id
        )
        self.assertRecordValues(entry_receivable_line, [{
            'reconciled': True,
            'amount_currency': -self.payment_be.amount,
            'amount_residual_currency': 0.0,
        }])

    def _post_payment_and_order(self):
        payment_method_line = self.inbound_payment_method_line
        usd = self.env.ref('base.USD')
        self.payment_be = self.env['account.payment'].create({
            'memo': self.sale_order_be.name,
            'amount': self.amount,
            'payment_type': 'inbound',
            'currency_id': usd.id,
            'partner_id': self.kenyian_partner.id,
            'partner_type': 'customer',
            'journal_id': self.payment_provider_be.journal_id.id,
            'company_id': self.payment_provider_be.company_id.id,
            'payment_method_line_id': payment_method_line.id,
            'payment_token_id': False,
            'invoice_ids': False,
        })
        self.payment_transaction_be = self.env['payment.transaction'].create({
            'payment_id': self.payment_be.id,
            'provider_id': self.payment_provider_be.id,
            'payment_method_id': self.payment_method_be.id,
            'operation': 'online_direct',
            'token_id': None,
            'partner_id': self.kenyian_partner.id,
            'amount': self.amount,
            'currency_id': usd.id,
            'sale_order_ids': self.sale_order_be.ids,
        })

        self.sale_order_be.company_id = self.company_ke
        self.sale_order_be.sudo().action_confirm()

        self.payment_be.action_post()
        self.payment_transaction_be.sudo()._set_done()
        self.payment_transaction_be.sudo()._post_process()

    def test_interco_accounting(self):
        self._check_accounting_installed()

        self._setup_outstanding_account()

        self._post_payment_and_order()
        self._check_payment_and_invoice()
        self._check_interco_move()

        self.assertTrue(self.payment_be.move_id)
        self._check_payment_move_reconciled()

    def test_interco_accounting_no_outstanding(self):
        self._check_accounting_installed()

        self._setup_outstanding_account(active=False)

        self._post_payment_and_order()
        self._check_payment_and_invoice()
        self._check_interco_move()

        self.assertFalse(self.payment_be.move_id)

    def test_interco_invoicing_with_outstanding(self):
        self._check_accounting_installed(expected=False)
        self._setup_outstanding_account(active=True)

        self._post_payment_and_order()
        self._check_payment_and_invoice()
        self._check_interco_move()

        self.assertTrue(self.payment_be.move_id)
        self._check_payment_move_reconciled()
