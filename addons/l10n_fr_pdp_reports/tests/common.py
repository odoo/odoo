from unittest.mock import patch

from odoo import Command, fields, models
from odoo.tests.common import TransactionCase


class PdpTestCommon(TransactionCase):
    # Use a date after Feb decade/month end to place transaction/payment flows in grace/closed by default.
    TEST_TODAY = fields.Date.from_string('2025-03-05')
    TEST_INVOICE_DATE = fields.Date.from_string('2025-02-05')
    TEST_PAYMENT_DATE = fields.Date.from_string('2025-02-15')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company_vals = {
            'name': "PDP Test Company",
            'country_id': cls.env.ref('base.fr').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'l10n_fr_pdp_enabled': True,
            'l10n_fr_pdp_sender_id': 'OD00',
            'l10n_fr_pdp_periodicity': 'decade',
            'l10n_fr_pdp_payment_periodicity': 'monthly',
            'l10n_fr_pdp_deadline_override_start': False,
            'l10n_fr_pdp_deadline_override_end': False,
            'siret': '12345678900000',
        }
        if 'generate_deferred_expense_entries_method' in cls.env['res.company']._fields:
            company_vals.update({
                'generate_deferred_expense_entries_method': 'manual',
                'deferred_expense_amount_computation_method': 'month',
                'generate_deferred_revenue_entries_method': 'manual',
                'deferred_revenue_amount_computation_method': 'month',
            })
        cls.company = cls.env['res.company'].create(company_vals)
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.env['ir.config_parameter'].sudo().set_param('PDP_TEST_ENV', '1')
        cls.company.partner_id.write({
            'vat': 'FR23334175221',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.company._l10n_fr_pdp_ensure_journal()

        # Accounts
        cls.income_account = cls.env['account.account'].with_company(cls.company.id).create({
            'name': "PDP Revenue",
            'code': 'PDP100',
            'account_type': 'income',
        })
        cls.expense_account = cls.env['account.account'].with_company(cls.company.id).create({
            'name': "PDP Expense",
            'code': 'PDP200',
            'account_type': 'expense',
        })
        receivable = cls.env['account.account'].with_company(cls.company.id).create({
            'name': "PDP Receivable",
            'code': 'PDP101',
            'account_type': 'asset_receivable',
            'reconcile': True,
        })
        payable = cls.env['account.account'].with_company(cls.company.id).create({
            'name': "PDP Payable",
            'code': 'PDP102',
            'account_type': 'liability_payable',
            'reconcile': True,
        })
        cls.bank_account = cls.env['account.account'].with_company(cls.company.id).create({
            'name': "PDP Bank Account",
            'code': 'PDPBANK',
            'account_type': 'asset_cash',
            'reconcile': True,
        })
        cls.company.transfer_account_id = cls.bank_account

        cls.partner_b2c = cls.env['res.partner'].create({
            'name': "B2C Customer",
            'country_id': cls.env.ref('base.fr').id,
            'property_account_receivable_id': receivable.id,
            'property_account_payable_id': payable.id,
        })
        cls.partner_international = cls.env['res.partner'].create({
            'name': "International Customer",
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',  # valid BE VAT for tests
            'property_account_receivable_id': receivable.id,
            'property_account_payable_id': payable.id,
        })

        cls.cash_basis_transition_account = cls.env['account.account'].with_company(cls.company.id).create({
            'name': "PDP Cash Basis Transition",
            'code': 'PDP103',
            'account_type': 'income',
        })
        cls.cash_basis_journal = cls.env['account.journal'].create({
            'name': "Cash Basis",
            'code': 'CBTX',
            'type': 'general',
            'company_id': cls.company.id,
        })
        cls.company.tax_cash_basis_journal_id = cls.cash_basis_journal
        cls.tax_20 = cls.env['account.tax'].create({
            'name': "VAT 20",
            'amount': 20,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': cls.company.id,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': cls.cash_basis_transition_account.id,
            'tax_group_id': cls.env['account.tax.group'].search([('country_id', '=', cls.env.ref('base.fr').id)], limit=1).id
                            or cls.env['account.tax.group'].create({
                                'name': "FR VAT",
                                'country_id': cls.env.ref('base.fr').id,
                            }).id,
        })
        cls.product = cls.env['product.product'].create({
            'name': "Test Product",
            'lst_price': 100,
            'taxes_id': [Command.set(cls.tax_20.ids)],
            'company_id': cls.company.id,
            'property_account_income_id': cls.income_account.id,
        })
        cls.service_product = cls.env['product.product'].create({
            'name': "Test Service",
            'type': 'service',
            'lst_price': 100,
            'taxes_id': [Command.set(cls.tax_20.ids)],
            'company_id': cls.company.id,
            'property_account_income_id': cls.income_account.id,
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': "PDP Bank",
            'code': 'PDBK',
            'type': 'bank',
            'company_id': cls.company.id,
            'default_account_id': cls.bank_account.id,
        })
        manual_method_line = (
            cls.bank_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'manual')[:1]
            or cls.bank_journal.inbound_payment_method_line_ids[:1]
        )
        if manual_method_line and not manual_method_line.payment_account_id:
            manual_method_line.payment_account_id = cls.bank_account

        # Ensure a clean slate
        cls.env['l10n.fr.pdp.flow'].sudo().search([('company_id', '=', cls.company.id)]).unlink()

    def setUp(self):
        super().setUp()
        self._context_today_patcher = patch('odoo.fields.Date.context_today', return_value=self.TEST_TODAY)
        self._date_today_patcher = patch('odoo.fields.Date.today', return_value=self.TEST_TODAY)
        self._context_today_patcher.start()
        self._date_today_patcher.start()
        self.addCleanup(self._context_today_patcher.stop)
        self.addCleanup(self._date_today_patcher.stop)
        self.env['l10n.fr.pdp.flow'].sudo().search([('company_id', '=', self.company.id)]).unlink()
        self.env['account.move'].sudo().search([
            ('company_id', '=', self.company.id),
            ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
            ('name', 'like', 'INV%'),
        ]).unlink()
        self.env['account.move'].sudo().search([
            ('company_id', '=', self.company.id),
            ('move_type', 'in', self.env['account.move'].get_purchase_types(include_receipts=False)),
        ]).unlink()
        self.env['account.payment'].sudo().search([
            ('company_id', '=', self.company.id),
        ]).unlink()
        self.env['account.move'].sudo().search([
            ('company_id', '=', self.company.id),
            ('journal_id', '=', self.bank_journal.id),
            ('name', 'like', 'BNK%'),
        ]).unlink()
        # Reset company identifiers/settings that tests may tweak.
        write_vals = {
            'siret': '12345678900000',
            'country_id': self.env.ref('base.fr').id,
            'l10n_fr_pdp_enabled': True,
            'l10n_fr_pdp_sender_id': 'OD00',
            'l10n_fr_pdp_periodicity': 'decade',
            'l10n_fr_pdp_payment_periodicity': 'monthly',
            'l10n_fr_pdp_tax_due_code': '3',
            'l10n_fr_pdp_deadline_override_start': False,
            'l10n_fr_pdp_deadline_override_end': False,
            'l10n_fr_pdp_send_mode': 'auto',
            'transfer_account_id': self.bank_account.id,
        }
        if 'generate_deferred_expense_entries_method' in self.company._fields:
            write_vals.update({
                'generate_deferred_expense_entries_method': 'manual',
                'deferred_expense_amount_computation_method': 'month',
                'generate_deferred_revenue_entries_method': 'manual',
                'deferred_revenue_amount_computation_method': 'month',
            })
        self.company.write(write_vals)
        self.company.partner_id.write({
            'vat': 'FR23334175221',
            'country_id': self.env.ref('base.fr').id,
        })

    # Helpers ---------------------------------------------------------------
    def _create_invoice(self, partner=None, date_val=None, sent=False, taxes=None, product=None):
        partner = partner or self.partner_b2c
        date_val = date_val or self.TEST_INVOICE_DATE
        taxes = taxes or self.tax_20
        product = product or self.product
        tax_ids = taxes.ids if isinstance(taxes, models.Model) else (taxes or [])
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': "PDP Sales",
                'code': 'PDSA',
                'type': 'sale',
                'company_id': self.company.id,
                'default_account_id': self.income_account.id,
            })
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': date_val,
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [Command.set(tax_ids)],
                'account_id': self.income_account.id,
            })],
        })
        move.action_post()
        if sent:
            move.is_move_sent = True
        return move

    def _create_vendor_bill(self, partner=None, date_val=None):
        partner = partner or self.partner_international
        date_val = date_val or self.TEST_INVOICE_DATE
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': "PDP Purchases",
                'code': 'PDPB',
                'type': 'purchase',
                'company_id': self.company.id,
                'default_account_id': self.expense_account.id,
            })
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': date_val,
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [Command.set(self.tax_20.ids)],
                'account_id': self.expense_account.id,
            })],
        })
        move.action_post()
        return move

    def _run_aggregation(self):
        # Clean previous flows for deterministic assertions
        self.env['l10n.fr.pdp.flow'].sudo().search([('company_id', '=', self.company.id)]).unlink()
        aggregator = self.env['l10n.fr.pdp.flow.aggregator']
        ctx = {**self.env.context, 'mail_create_nolog': True, 'tracking_disable': True}
        return aggregator.with_context(ctx)._cron_process_company(self.company)

    def _aggregate_company(self):
        """Run the PDP aggregator without clearing existing flows."""
        aggregator = self.env['l10n.fr.pdp.flow.aggregator']
        ctx = {**self.env.context, 'mail_create_nolog': True, 'tracking_disable': True}
        return aggregator.with_context(ctx)._cron_process_company(self.company)

    def _get_single_flow(self):
        return self.env['l10n.fr.pdp.flow'].search([('company_id', '=', self.company.id)])

    def _create_payment_for_invoice(self, invoice, amount=None, pay_date=None):
        """Create and post a customer payment and reconcile with the invoice."""
        amount = amount or invoice.amount_total
        pay_date = pay_date or self.TEST_PAYMENT_DATE
        journal = self.bank_journal
        # In "all" runs, the accountant stack may be installed, meaning `account.payment`
        # will not auto-fill an outstanding account unless a payment method line provides it.
        method_line = (
            journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'manual')[:1]
            or journal.inbound_payment_method_line_ids[:1]
        )
        if not method_line:
            raise AssertionError('Test bank journal must have at least one inbound payment method line.')
        if not method_line.payment_account_id:
            method_line.payment_account_id = journal.default_account_id or self.bank_account
        payment = self.env['account.payment'].with_context(mail_create_nolog=True, tracking_disable=True).with_company(self.company.id).create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': amount,
            'date': pay_date,
            'journal_id': journal.id,
            'payment_method_line_id': method_line.id,
        })
        payment.action_post()
        payment_lines = payment.move_id.line_ids
        receivable_line = payment_lines.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        if receivable_line:
            inv_receivable = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable').account_id
            receivable_line.account_id = inv_receivable
        (invoice.line_ids + payment_lines).filtered(
            lambda l: l.account_id.reconcile and l.account_id.account_type == 'asset_receivable',
        ).reconcile()
        return payment
