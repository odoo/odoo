from odoo.addons.account.tests.test_account_payment import TestAccountPayment
from odoo import Command, SUPERUSER_ID
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGeneratePayorderData(TestAccountPayment):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')

        cls.enet_rtgs_method_id = cls.env.ref('l10n_in_enet_batch_payment.account_payment_method_enet_rtgs').id

        cls.bank_journal_1.outbound_payment_method_line_ids |= cls.env['account.payment.method.line'].create(
            {"payment_method_id": cls.enet_rtgs_method_id}
        )
        cls.enet_rtgs_line_bank_journal_1 = cls.bank_journal_1.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'enet_rtgs')

        # Bank Journal Configuration
        cls.bank_journal_1.with_user(SUPERUSER_ID).write({
            'enet_template_field_ids': [
                Command.create({
                    'field_name': 'payment_method_line_id.display_name',
                    'label': 'Transaction Type',
                }),
                Command.create({
                    'field_name': 'partner_id.name',
                    'label': 'Beneficiary Name',
                }),
                Command.create({
                    'field_name': 'amount',
                    'label': 'Amount'
                }),
                Command.create({
                    'field_name': 'partner_bank_id.acc_number',
                    'label': 'Beneficiary Account Number'
                }),
            ]
        })

        # Payments
        cls.payment1 = cls.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': cls.partner_a.id,
            'payment_method_line_id': cls.enet_rtgs_line_bank_journal_1.id,
            'journal_id': cls.bank_journal_1.id
        })
        cls.payment1.partner_bank_id.allow_out_payment = True
        cls.payment1.action_post()

        cls.payment2 = cls.env['account.payment'].create({
            'amount': 200.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': cls.partner_a.id,
            'payment_method_line_id': cls.enet_rtgs_line_bank_journal_1.id,
            'journal_id': cls.bank_journal_1.id
        })
        cls.payment2.partner_bank_id.allow_out_payment = True
        cls.payment2.action_post()

        # Batch Payment
        cls.batch_payment = cls.env['account.batch.payment'].create({
            'journal_id': cls.bank_journal_1.id,
            'payment_ids': [(4, payment.id, None) for payment in (cls.payment1 | cls.payment2)],
            'payment_method_id': cls.enet_rtgs_method_id,
            'batch_type': 'outbound',
        })
        cls.batch_payment.validate_batch()

    # Testing payorder data for a batch
    def test_csv_data(self):
        data = self.batch_payment.get_csv_data().splitlines()

        header = (
            'Transaction Type,Beneficiary Name,Amount,Beneficiary Account Number'
        )
        self.assertEqual(data[0], header, "Didn't generate the expected header")

        expected_csv_lines = [(
            'ENet RTGS (Bank),partner_a,100.0,0123456789'
        ), (
            'ENet RTGS (Bank),partner_a,200.0,0123456789'
        )]
        self.assertEqual(data[1], expected_csv_lines[0], "Didn't generate the expected lines for Payment1")
        self.assertEqual(data[2], expected_csv_lines[1], "Didn't generate the expected lines for Payment2")
        self.assertEqual(len(data), 3, "It should exactly generate the three lines above")
