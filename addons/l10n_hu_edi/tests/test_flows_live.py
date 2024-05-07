from odoo import tools
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import L10nHuEdiConnection, L10nHuEdiConnectionError

from unittest import skipIf, mock
import contextlib
from datetime import timedelta

TEST_CRED = {}
last_invoice = {'INV/2024/': 20, 'RINV/2024/': 12}
with contextlib.suppress(ImportError):
    # Private credentials.py. Sorry, we can't share this file.
    from .credentials import TEST_CRED, last_invoice


@tagged('external_l10n', 'external', 'post_install', '-at_install', '-standard', '-post_install_l10n')
@skipIf(not TEST_CRED, 'no NAV credentials')
class L10nHuEdiTestFlowsLive(L10nHuEdiTestCommon, TestAccountMoveSendCommon):
    """ Test the Hungarian EDI flows with the NAV test servers. """

    # === Overrides === #

    @classmethod
    def write_edi_credentials(cls):
        # OVERRIDE
        return cls.company_data['company'].write({**TEST_CRED})

    # === Tests === #

    def test_send_invoice_and_credit_note(self):
        invoice = self.create_invoice_simple()
        with self.set_invoice_name(invoice, 'INV/2024/'):
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, l10n_hu_edi_enable_nav_30=True)
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

        credit_note = self.create_reversal(invoice)
        with self.set_invoice_name(credit_note, 'RINV/2024/'):
            credit_note.action_post()
            send_and_print = self.create_send_and_print(credit_note, l10n_hu_edi_enable_nav_30=True)
            send_and_print.action_send_and_print()
            self.assertRecordValues(credit_note, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': 1}])

            cancel_wizard = self.env['l10n_hu_edi.cancellation'].with_context({"default_invoice_id": credit_note.id}).create({
                'code': 'ERRATIC_DATA',
                'reason': 'Some reason...',
            })
            cancel_wizard.button_request_cancel()
            self.assertRecordValues(credit_note, [{'l10n_hu_edi_state': 'cancel_pending', 'l10n_hu_invoice_chain_index': 1}])

    def test_send_advance_final_invoice(self):
        # Skip if sale is not installed
        if 'sale_line_ids' not in self.env['account.move.line']:
            self.skipTest('Sale module not installed, skipping advance invoice tests.')

        advance_invoice, final_invoice = self.create_advance_invoice()
        with self.set_invoice_name(advance_invoice, 'INV/2024/'):
            advance_invoice.action_post()
            send_and_print = self.create_send_and_print(advance_invoice, l10n_hu_edi_enable_nav_30=True)
            send_and_print.action_send_and_print()
            self.assertRecordValues(advance_invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

        with self.set_invoice_name(final_invoice, 'INV/2024/'):
            final_invoice.action_post()
            send_and_print = self.create_send_and_print(final_invoice, l10n_hu_edi_enable_nav_30=True)
            send_and_print.action_send_and_print()
            self.assertRecordValues(final_invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

    def test_send_invoice_complex_huf(self):
        invoice = self.create_invoice_complex_huf()
        with self.set_invoice_name(invoice, 'INV/2024/'):
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, l10n_hu_edi_enable_nav_30=True)
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

    def test_send_invoice_complex_eur(self):
        invoice = self.create_invoice_complex_eur()
        with self.set_invoice_name(invoice, 'INV/2024/'):
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, l10n_hu_edi_enable_nav_30=True)
            send_and_print.action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

    def test_timeout_recovery_fail(self):
        invoice = self.create_invoice_simple()
        invoice.action_post()

        send_and_print = self.create_send_and_print(invoice, l10n_hu_edi_enable_nav_30=True)
        with self.patch_call_nav_endpoint('manageInvoice', make_request=False), contextlib.suppress(UserError):
            send_and_print.action_send_and_print()

        self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'send_timeout', 'l10n_hu_invoice_chain_index': -1}])

        # Set the send time 7 minutes in the past so the timeout recovery mechanism triggers.
        invoice.l10n_hu_edi_send_time -= timedelta(minutes=7)
        with contextlib.suppress(UserError):
            invoice.l10n_hu_edi_button_update_status()
        self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'rejected', 'l10n_hu_invoice_chain_index': 0}])

    def test_timeout_recovery_success(self):
        invoice = self.create_invoice_simple()
        with self.set_invoice_name(invoice, 'INV/2024/'):
            invoice.action_post()
            send_and_print = self.create_send_and_print(invoice, l10n_hu_edi_enable_nav_30=True)
            with self.patch_call_nav_endpoint('manageInvoice'), contextlib.suppress(UserError):
                send_and_print.action_send_and_print()

            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'send_timeout', 'l10n_hu_invoice_chain_index': -1}])

            # Set the send time 7 minutes in the past so the timeout recovery mechanism triggers.
            invoice.l10n_hu_edi_send_time -= timedelta(minutes=7)
            invoice.l10n_hu_edi_button_update_status()
            self.assertRecordValues(invoice, [{'l10n_hu_edi_state': 'confirmed', 'l10n_hu_invoice_chain_index': -1}])

    # === Helpers === #

    @contextlib.contextmanager
    def set_invoice_name(self, invoice, prefix):
        try:
            last_invoice[prefix] = last_invoice.get(prefix, 0) + 1
            invoice.name = f'{prefix}{last_invoice[prefix]:05}'
            yield
        finally:
            if invoice.l10n_hu_edi_state not in ['confirmed', 'confirmed_warning', 'cancel_sent', 'cancel_pending', 'cancelled']:
                last_invoice[prefix] -= 1
            else:
                with tools.file_open('l10n_hu_edi/tests/credentials.py', 'a') as credentials_file:
                    credentials_file.write(f'last_invoice = {last_invoice}\n')

    @contextlib.contextmanager
    def patch_call_nav_endpoint(self, endpoint, make_request=True):
        """ Patch _call_nav_endpoint in l10n_hu_edi.connection, so that a Timeout is raised on the specified endpoint.

        :param endpoint: the endpoint for which to raise a Timeout
        :param make_request bool: If true, will still make the request before raising the timeout.
        """
        real_call_nav_endpoint = L10nHuEdiConnection._call_nav_endpoint

        def mock_call_nav_endpoint(self, mode, service, data, timeout=20):
            if service == endpoint:
                if make_request:
                    real_call_nav_endpoint(self, mode, service, data, timeout=timeout)
                raise L10nHuEdiConnectionError('Freeze! This is a timeout!', code='timeout')
            else:
                return real_call_nav_endpoint(self, mode, service, data, timeout=timeout)

        with mock.patch.object(L10nHuEdiConnection, '_call_nav_endpoint', new=mock_call_nav_endpoint):
            yield
