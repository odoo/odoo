from base64 import b64decode as bsf_decode
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_it_riba.tools import riba


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestRiba(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('it')
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None
        company = cls.company_data['company']
        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')
        company.write({
            'name': 'Dàmone Srl',
            'street': 'Via Silvio Pellico 12',
            'city': "Palazzolo sull'Oglio",
            'vat': 'IT03821260985',
            'l10n_it_codice_fiscale': '03821260985',
            'l10n_it_sia_code': '12345',
        })
        partner_bank = cls.env['res.bank'].create({
            'name': 'CRA di Borgo San Giacomo Credito Cooperativo SCRL',
        })
        cls.partner_bank_account = cls.env['res.partner.bank'].create({
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
            'acc_number': 'IT94W0333201600000001112418',
            'bank_id': partner_bank.id,
            'allow_out_payment': True,
        })
        isernia = cls.env.ref('base.state_it_is')
        cls.partner_a.write({
            'name': 'Aluvetraro Srl',
            'street': 'Via Marco Alberti 245',
            'city': isernia.name,
            'zip': '86170',
            'state_id': isernia.id,
            'country_id': cls.env.ref('base.it').id,
            'vat': 'IT03450700988',
            'l10n_it_codice_fiscale': '03450700988',
        })
        cls.riba_method = cls.env.ref('l10n_it_riba.payment_method_riba')
        cls.riba_payment_line = cls.env['account.payment.method.line'].with_company(company).search([
            ('code', '=', 'riba'), ('journal_id.code', '=', 'BNK1'), ('company_id', '=', cls.company.id)
        ])
        cls.riba_payment_line.payment_account_id = cls.env['account.account'].create({
            'name': "Outstanding Payments",
            'prefix': company.bank_account_code_prefix,
            'code_digits': 6,
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.riba_payment_terms = cls.env['account.payment.term'].with_company(company).create([
            {
                'name': name,
                'line_ids': [Command.create({
                    'nb_days': gg,
                    'delay_type': "days_end_of_month_on_the",
                    'days_next_month': 0,
                })],
            } for name, gg in (
                ('Ri.Ba. 30gg FM', 30),
                ('Ri.Ba. 60gg FM', 60)
            )
        ])
        journal_bank = cls.company_data['default_journal_bank']
        journal_bank.bank_account_id = cls.env['res.partner.bank'].create({
            'acc_number': 'IT60X0542811101000000123456',
            'partner_id': company.partner_id.id,
            'acc_type': 'bank',
            'allow_out_payment': True,
        })
        sale_tax = company.account_sale_tax_id
        cls.invoices = cls.env['account.move'].with_company(company).create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2024-11-22',
                'invoice_payment_term_id': payment_term,
                'partner_id': cls.partner_a.id,
                'partner_bank_id': cls.partner_bank_account.id,
                'invoice_line_ids': [
                     Command.create({
                        'name': 'line 1',
                        'quantity': 1,
                        'price_unit': amount,
                        'tax_ids': [(6, 0, [sale_tax.id])]
                    })
                ],
            }
            for amount, payment_term in zip(
                (153.0, 100.0),
                cls.riba_payment_terms.ids
            )
        ])
        cls.invoices._post()

    def _expected_content(self, payment_ids):
        return (
              " IB1234505428221124BATCH/IN/2024/0001                                                                            E      "
            "\n 140000001            221124300000000000010000-05428111010000001234560333201600            123454Aluvetraro Srl        E"
            "\n 200000001Da'mone Srl             Via Silvio Pellico 12   Palazzolo sull'Oglio                                          "
            "\n 300000001Aluvetraro Srl                                              03450700988                                       "
            "\n 400000001Via Marco Alberti 245         86170Isernia                ISCRA di Borgo San Giacomo Credito Cooperativo SCRL "
            "\n 500000001Invoice INV/2024/00001 Amount 100.00                                                      03821260985         "
           f"\n 510000001{payment_ids[0]:>010}Da'mone Srl                                                                                         "
            "\n 700000001                                                                                                              "
            "\n 140000002            221124300000000000015300-05428111010000001234560333201600            123454Aluvetraro Srl        E"
            "\n 200000002Da'mone Srl             Via Silvio Pellico 12   Palazzolo sull'Oglio                                          "
            "\n 300000002Aluvetraro Srl                                              03450700988                                       "
            "\n 400000002Via Marco Alberti 245         86170Isernia                ISCRA di Borgo San Giacomo Credito Cooperativo SCRL "
            "\n 500000002INV/2024/00002 Amount 153.00                                                              03821260985         "
           f"\n 510000002{payment_ids[1]:>010}Da'mone Srl                                                                                         "
            "\n 700000002                                                                                                              "
            "\n EF1234505428221124BATCH/IN/2024/0001        00000020000000000253000000000000000000000016                        E      "
            "\n"
        )

    def _create_payment_batch_and_reconcile(self, invoices):
        data = [(100.0, False), (153.0, 'INV/2024/00002')]
        payments = self.env['account.payment'].create([{
            'amount': amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.riba_payment_line.id,
            'destination_account_id': self.partner_a.property_account_receivable_id.id,
            'partner_bank_id': self.partner_bank_account.id,
            'memo': memo,
        } for amount, memo in data])
        payments.action_post()
        batch_payment = self.env['account.batch.payment'].create({
            'journal_id': payments.journal_id.id,
            'payment_method_id': payments.payment_method_id.id,
            'payment_ids': [Command.set(payments.ids)],
        })
        for invoice, payment in zip(invoices, batch_payment.payment_ids):
            lines = (invoice.line_ids + payment.move_id.line_ids) \
                .filtered(lambda x: x.account_id.account_type == 'asset_receivable')
            lines.reconcile()
        batch_payment.validate_batch()
        return batch_payment

    @freeze_time('2024-11-22')
    def test_riba_export(self):
        batch_payment = self._create_payment_batch_and_reconcile(self.invoices)
        actual_exported_content = bsf_decode(batch_payment.export_file).decode()
        self.assertEqual(actual_exported_content, self._expected_content(batch_payment.payment_ids.ids))

    @freeze_time('2024-11-22')
    def test_riba_import(self):
        batch_payment = self._create_payment_batch_and_reconcile(self.invoices)
        original_riba_values = batch_payment._l10n_it_riba_get_values()
        actual_imported_values = riba.file_import(self._expected_content(batch_payment.payment_ids.ids))
        self.assertTrue(riba.eq_records(actual_imported_values, original_riba_values))
