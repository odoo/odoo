from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command

from odoo.tests import Form, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_pl.tests.utils.utils import FakeResponse


def _make_request_patched(self, endpoint, params=None):
    return FakeResponse(endpoint)


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestL10nPlBankAccountVerification(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()

        cls.verification_sudo = cls.env['l10n_pl.bank.account.verification'].sudo()
        cls.pl_supplier, cls.pl_supplier_bank_account, cls.pl_supplier_move = cls._create_partner_bank_and_move(cls, '1111111111', 'PL61109010140000071219812874')  # valid bank account number
        cls.startClassPatcher(freeze_time('2026-01-31 10:00:00'))

    def _create_payments_for_moves(self, moves):
        action_register_payment = moves.action_register_payment()
        self.assertTrue(action_register_payment)
        wizard = self.env[action_register_payment['res_model']].with_context(action_register_payment['context']).create({})

        action_create_payment = wizard.action_create_payments()
        if action_create_payment.get('res_id'):
            return self.env[action_create_payment['res_model']].browse(action_create_payment['res_id'])
        return self.env[action_create_payment['res_model']].search(action_create_payment['domain'])

    def _create_payment(self, payment_type='outbound', partner=None, amount=15000, journal=False, payment_method=False, partner_bank=False, post=True):
        partner = partner or self.pl_supplier
        journal = journal or self.company_data['default_journal_bank']
        payment_method = journal.outbound_payment_method_line_ids[0]
        partner_bank = partner_bank or partner.bank_ids[0]

        payment = self.env['account.payment'].with_company(self.company_data['company']).create({
            'payment_type': payment_type,
            'partner_id': partner.id,
            'amount': amount,
            'journal_id': journal.id,
            'payment_method_line_id': payment_method.id,
            'partner_bank_id': partner_bank.id,
        })

        if post:
            payment.action_post()
        return payment

    def _create_partner_bank_and_move(self, vat, account_number=False, amount=15000, country='pl', post_move=True):
        supplier = self.env['res.partner'].create({
            'name': f'Other {country} supplier',
            'street': 'Church street, 45',
            'city': 'Los Alamos',
            'zip': '1234',
            'country_id': self.env.ref(f'base.{country}').id,
            'vat': vat,
        })
        bank_account = self.env['res.partner.bank']
        if account_number:
            bank_account = self.env['res.partner.bank'].create({
                'account_number': account_number,
                'partner_id': supplier.id,
            })
        move = self.env['account.move'].create({
            'partner_id': supplier.id,
            'move_type': 'in_invoice',
            'invoice_date': '2026-02-16',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test sale',
                'price_unit': amount,
            })]
        })
        if post_move:
            move.action_post()
        return supplier, bank_account, move

    def _check_form_fields(self, moves, invalid_bank_accounts=False, not_found_partners=False, incomplete_partners=False):
        """
        invalid_bank_accounts: bank account number is not linked to partner vat in gov files
        not_found_partners: partners with a vat not found in gov files
        incomplete_partners: no api call, partner missing a vat or a bank account
        """
        with Form.from_action(self.env, moves.action_register_payment()) as wiz_form:
            self.assertEqual(wiz_form.l10n_pl_bank_verification_invalid_bank_account_ids.ids, (invalid_bank_accounts or self.env['res.partner.bank']).ids)
            self.assertEqual(wiz_form.l10n_pl_not_found_partner_ids.ids, (not_found_partners or self.env['res.partner']).ids)
            self.assertEqual(wiz_form.l10n_pl_incomplete_data_partner_ids.ids, (incomplete_partners or self.env['res.partner']).ids)

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_single_payment_with_valid_bank_account_check(self):
        self._check_form_fields(self.pl_supplier_move)

        payment = self._create_payments_for_moves(self.pl_supplier_move)

        self.assertRecordValues(payment.l10n_pl_verification_id, [{
            'verification_status': 'valid',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'verification_request_id': 'AZERTYUIOP-01',
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_single_payment_with_verification_done_day_before_should_check_again(self):
        self.verification_sudo.create({
            'verification_status': 'valid',
            'verification_request_id': 'AZERTYUIOP-99',
            'verification_timestamp': datetime(2026, 1, 30, 10, 0, 0),
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        })
        self._check_form_fields(self.pl_supplier_move)
        payment = self._create_payments_for_moves(self.pl_supplier_move)
        self.assertRecordValues(payment.l10n_pl_verification_id, [{
            'verification_status': 'valid',
            'verification_request_id': 'AZERTYUIOP-01',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_single_payment_with_invalid_or_missing_vat(self):
        # partner has no vat and no bank account
        supplier, _bank_account, move = self._create_partner_bank_and_move(vat=False)

        self._check_form_fields(move, incomplete_partners=supplier)

        # assign a vat number but still no bank account
        supplier.vat = '0000000000'
        self._check_form_fields(move, incomplete_partners=supplier)

        # assign a bank account number
        bank_account = self.pl_supplier_bank_account = self.env['res.partner.bank'].create({
            'account_number': '61109010140000071219812870',
            'partner_id': supplier.id,
        })
        self._check_form_fields(move, not_found_partners=supplier)

        payment = self._create_payments_for_moves(move)
        self.assertRecordValues(payment.l10n_pl_verification_id, [{
            'verification_status': 'not_found_partner',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'verification_request_id': 'AZERTYUIOP-15',
            'partner_bank_id': bank_account.id,
            'partner_bank_account_number': bank_account.sanitized_account_number,
            'partner_id': supplier.id,
            'partner_vat': supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_single_payment_with_null_subject_result(self):
        supplier, supplier_bank, move = self._create_partner_bank_and_move('PL3333333333', '61109010140000071219812999')  # invalid bank account number
        self._check_form_fields(move, invalid_bank_accounts=supplier_bank)
        payment = self._create_payments_for_moves(move)
        self.assertRecordValues(payment.l10n_pl_verification_id, [{
            'verification_status': 'invalid',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'verification_request_id': 'AZERTYUIOP-04',
            'partner_bank_id': supplier_bank.id,
            'partner_bank_account_number': supplier_bank.sanitized_account_number,
            'partner_id': supplier.id,
            'partner_vat': supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_multiple_payments_with_an_invalid_vat(self):
        supplier, supplier_bank, move = self._create_partner_bank_and_move('0000000000', '61109010140000071219812870')  # not found vat number
        moves = move + self.pl_supplier_move
        self._check_form_fields(moves, not_found_partners=supplier)

        date = datetime(2026, 1, 31, 10, 0, 0)

        payments = self._create_payments_for_moves(moves)
        self.assertRecordValues(payments.l10n_pl_verification_id, [
            {
                'verification_status': 'not_found_partner',
                'verification_timestamp': date,
                'verification_request_id': 'AZERTYUIOP-02',
                'partner_bank_id': supplier_bank.id,
                'partner_bank_account_number': supplier_bank.sanitized_account_number,
                'partner_id': supplier.id,
                'partner_vat': supplier.vat,
            },
            {
                'verification_status': 'valid',
                'verification_timestamp': date,
                'verification_request_id': 'AZERTYUIOP-02',
                'partner_bank_id': self.pl_supplier_bank_account.id,
                'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
                'partner_id': self.pl_supplier.id,
                'partner_vat': self.pl_supplier.vat,
            },
        ])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_multiple_payments_with_valid_bank_account_check(self):
        supplier, supplier_bank, move = self._create_partner_bank_and_move('2222222222', '61109010140000071219812875')  # valid bank account number
        moves = move + self.pl_supplier_move
        self._check_form_fields(moves)

        date = datetime(2026, 1, 31, 10, 0, 0)

        payments = self._create_payments_for_moves(moves)
        self.assertRecordValues(payments.l10n_pl_verification_id, [
            {
                'verification_status': 'valid',
                'verification_timestamp': date,
                'verification_request_id': 'AZERTYUIOP-03',
                'partner_bank_id': supplier_bank.id,
                'partner_bank_account_number': supplier_bank.sanitized_account_number,
                'partner_id': supplier.id,
                'partner_vat': supplier.vat,
            },
            {
                'verification_status': 'valid',
                'verification_timestamp': date,
                'verification_request_id': 'AZERTYUIOP-03',
                'partner_bank_id': self.pl_supplier_bank_account.id,
                'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
                'partner_id': self.pl_supplier.id,
                'partner_vat': self.pl_supplier.vat,
            },
        ])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_multiple_payments_with_one_bank_account_not_found(self):
        supplier, bank_account, move = self._create_partner_bank_and_move('PL2222222222', '61109010140000071219812800')  # invalid bank account number
        moves = move + self.pl_supplier_move
        self._check_form_fields(moves, invalid_bank_accounts=bank_account)

        date = datetime(2026, 1, 31, 10, 0, 0)

        payments = self._create_payments_for_moves(moves)
        self.assertRecordValues(payments.l10n_pl_verification_id, [
            {
                'verification_status': 'invalid',
                'verification_request_id': 'AZERTYUIOP-03',
                'verification_timestamp': date,
                'partner_bank_id': bank_account.id,
                'partner_bank_account_number': bank_account.sanitized_account_number,
                'partner_id': supplier.id,
                'partner_vat': supplier.vat,
            },
            {
                'verification_status': 'valid',
                'verification_request_id': 'AZERTYUIOP-03',
                'verification_timestamp': date,
                'partner_bank_id': self.pl_supplier_bank_account.id,
                'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
                'partner_id': self.pl_supplier.id,
                'partner_vat': self.pl_supplier.vat,
            },
        ])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_multiple_payments_with_one_result_empty(self):
        supplier, bank_account, move = self._create_partner_bank_and_move('PL3333333333', '61109010140000071219812999')  # invalid bank account number
        moves = move + self.pl_supplier_move
        self._check_form_fields(moves, invalid_bank_accounts=bank_account)
        date = datetime(2026, 1, 31, 10, 0, 0)

        payments = self._create_payments_for_moves(moves)
        self.assertRecordValues(payments.l10n_pl_verification_id, [
            {
                'verification_status': 'invalid',
                'verification_request_id': 'AZERTYUIOP-05',
                'verification_timestamp': date,
                'partner_bank_id': bank_account.id,
                'partner_bank_account_number': bank_account.sanitized_account_number,
                'partner_id': supplier.id,
                'partner_vat': supplier.vat,
            },
            {
                'verification_status': 'valid',
                'verification_request_id': 'AZERTYUIOP-05',
                'verification_timestamp': date,
                'partner_bank_id': self.pl_supplier_bank_account.id,
                'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
                'partner_id': self.pl_supplier.id,
                'partner_vat': self.pl_supplier.vat,
            },
        ])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request')
    def test_register_payments_of_accounts_already_checked_dont_call_api(self, _make_request_not_called_patched):
        # At date, if the bank account was already checked, we shouldn't call the API
        self.verification_sudo.create({
            'verification_status': 'valid',
            'verification_request_id': 'AZERTYUIOP-99',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        })

        self._check_form_fields(self.pl_supplier_move)
        _make_request_not_called_patched.assert_not_called()

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request')
    def test_register_payment_of_account_already_checked_failed_dont_call_api_if_data_is_the_same(self, _make_request_not_called_patched):
        supplier, _bank_account, move = self._create_partner_bank_and_move('1111111111')
        self.verification_sudo.create({
            'verification_status': 'incomplete_partner',
            'verification_request_id': False,
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'partner_bank_id': False,
            'partner_bank_account_number': False,
            'partner_id': supplier.id,
            'partner_vat': supplier.vat,
        })

        # Datas are the same, shouldn't call the api
        self._check_form_fields(move, incomplete_partners=supplier)
        _make_request_not_called_patched.assert_not_called()

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_register_payment_under_verification_limit(self):
        move = self.env['account.move'].create({
            'partner_id': self.pl_supplier.id,
            'move_type': 'in_invoice',
            'invoice_date': '2026-02-16',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test sale',
                'price_unit': 500,
            })]
        })
        move.action_post()
        self._check_form_fields(move)

        _supplier, _bank_account, move_other_partner = self._create_partner_bank_and_move('PL2222222222', '61109010140000071219812800', amount=500)

        moves = self.pl_supplier_move + move + move_other_partner
        self._check_form_fields(moves)

        payments = self._create_payments_for_moves(moves)
        self.assertRecordValues(payments.l10n_pl_verification_id, [{
            'verification_status': 'valid',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'verification_request_id': 'AZERTYUIOP-01',
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request')
    def test_register_payment_for_non_pl_supplier(self, _make_request_not_called_patched):
        _supplier, _bank_account, move = self._create_partner_bank_and_move('BE0477472701', country='be')
        self._check_form_fields(move)

        payments = self._create_payments_for_moves(move)
        self.assertFalse(payments.l10n_pl_verification_id)
        _make_request_not_called_patched.assert_not_called()

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request')
    def test_register_payment_for_non_pl_company(self, _make_request_not_called_patched):
        self.company_data['company'].country_id = self.env.ref('base.be')
        self._check_form_fields(self.pl_supplier_move)

        payments = self._create_payments_for_moves(self.pl_supplier_move)
        self.assertFalse(payments.l10n_pl_verification_id)
        _make_request_not_called_patched.assert_not_called()

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_create_single_payment_valid_partner(self):
        payment = self._create_payment()
        self.assertRecordValues(payment.l10n_pl_verification_id, [{
            'verification_status': 'valid',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'verification_request_id': 'AZERTYUIOP-01',
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_create_single_payment_invalid_bank_account(self):
        self.pl_supplier_bank_account.account_number = 'PL61109010140000071219812999'  # invalid
        payment = self._create_payment()
        self.assertRecordValues(payment.l10n_pl_verification_id, [{
            'verification_status': 'invalid',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'verification_request_id': 'AZERTYUIOP-01',
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        }])

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request')
    def test_create_single_payment_for_already_checked_bank_account(self, _make_request_not_called_patched):
        old_verif = self.verification_sudo.create({
            'verification_status': 'valid',
            'verification_request_id': 'AZERTYUIOP-99',
            'verification_timestamp': datetime(2026, 1, 31, 10, 0, 0),
            'partner_bank_id': self.pl_supplier_bank_account.id,
            'partner_bank_account_number': self.pl_supplier_bank_account.sanitized_account_number,
            'partner_id': self.pl_supplier.id,
            'partner_vat': self.pl_supplier.vat,
        })
        payment = self._create_payment()
        self.assertEqual(payment.l10n_pl_verification_id, old_verif)
        _make_request_not_called_patched.assert_not_called()

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_create_single_payment_and_update_vat(self):
        self.pl_supplier.vat = '0000000000'
        payment = self._create_payment()
        verif = payment.l10n_pl_verification_id
        self.assertTrue(verif)
        self.pl_supplier.vat = '1111111111'
        payment_2 = self._create_payment()
        self.assertNotEqual(verif, payment_2.l10n_pl_verification_id)

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_create_single_payment_for_partner_with_2_bank_accounts(self):
        # Partner has 2 bank accounts: 1 valid and 1 invalid
        self.env['res.partner.bank'].create({
            'account_number': 'PL61109010140000071219812000',  # invalid
            'partner_id': self.pl_supplier.id,
        })
        # A verification will be created for both bank account, but the payment register wizard should not display
        # information about the 2nd account as the payment is done with the 1st bank account
        self._check_form_fields(self.pl_supplier_move)

    @patch('odoo.addons.l10n_pl.models.bank_account_verification.BankAccountVerification._make_request', _make_request_patched)
    def test_no_verification_duplicated(self):
        # Create a verification for the bank account
        self._check_form_fields(self.pl_supplier_move)
        verification = self.env['l10n_pl.bank.account.verification'].search([])
        verification_start_count = len(verification)

        # Create a second bank account and trigger the verification creation
        second_bank_account = self.env['res.partner.bank'].create({
            'account_number': 'PL61109010140000071219812000',  # invalid
            'partner_id': self.pl_supplier.id,
        })
        move = self.env['account.move'].create({
            'partner_id': self.pl_supplier.id,
            'move_type': 'in_invoice',
            'invoice_date': '2026-02-16',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_bank_id': second_bank_account.id,  # Set second bank account for payment
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test sale',
                'price_unit': 16000,
            })]
        })
        move.action_post()
        self._check_form_fields(move, invalid_bank_accounts=second_bank_account)
        # Only 2 verifications should have been created: 1 for each bank account
        verifications = self.env['l10n_pl.bank.account.verification'].search([])
        self.assertEqual(len(verifications), verification_start_count + 1)
