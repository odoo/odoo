# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

CONTACT_PROXY_METHOD = 'odoo.addons.l10n_my_edi.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_my_edi_contact_proxy'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestReceivedDocuments(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
        })
        cls.partner_a.write({
            'vat': 'C2584563201',
            'country_id': cls.env.ref('base.my').id,
        })
        # We use demo to register without triggering any api calls.
        cls.proxy_user = cls.env['account_edi_proxy_client.user']._register_proxy_user(cls.company_data['company'], 'l10n_my_edi', 'demo')
        cls.proxy_user.edi_mode = 'test'
        # Not registered to MyInvois, and not in MYR.
        cls.other_company_data = cls.setup_other_company(currency_id=cls.env.ref('base.USD').id)

    def _document_data(self, uuid, **values):
        """ A received document, as returned by the proxy. """
        return {
            'uuid': uuid,
            'submission_uid': f'SUB-{uuid}',
            'long_id': f'LONG-{uuid}',
            'internal_id': f'IV-{uuid}',
            'document_type': '01',
            'status': 'valid',
            'supplier_tin': 'C2584563201',
            'supplier_name': 'Partner A',
            'issuance_datetime': '2024-07-10T02:00:00Z',
            'validation_datetime': '2024-07-10T02:05:00Z',
            'total': 1000.0,
            **values,
        }

    def _sync(self, pages, month='2024-07-01'):
        """ Run the sync wizard, the proxy returning the given pages of documents.

        :return: the action returned by the wizard and the params of the calls to the proxy.
        """
        calls = []

        def mock_contact_proxy(proxy_user, endpoint, params):
            self.assertEqual(endpoint, 'api/l10n_my_edi/1/search_received_documents')
            calls.append(params)
            return {'documents': pages[params['page'] - 1], 'page_count': len(pages)}

        wizard = self.env['myinvois.document.sync.wizard'].create({
            'month': month,
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        with patch(CONTACT_PROXY_METHOD, new=mock_contact_proxy):
            action = wizard.button_sync()
        return action, calls

    def _get_received_bills(self, uuids):
        return self.env['myinvois.document'].search([('myinvois_external_uuid', 'in', uuids)]).invoice_ids

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_creates_draft_bills(self):
        """ Each new valid document becomes a draft bill with a single line holding its total. """
        action, calls = self._sync([[
            self._document_data('DOC1'),
            # Issued on 2024-07-11 in Malaysia, which is still the 10th in UTC.
            self._document_data('DOC2', document_type='02', supplier_tin='C9999999999', supplier_name='New Supplier', total=50.0, issuance_datetime='2024-07-10T17:00:00Z'),
            # Self-billed documents received by the company were issued by its customers: they are not bills.
            self._document_data('DOC3', document_type='11'),
        ]])

        self.assertEqual(calls, [{
            'date_from': '2024-07-01T00:00:00+08:00',
            'date_to': '2024-07-31T23:59:59+08:00',
            'page': 1,
        }])
        bills = self._get_received_bills(['DOC1', 'DOC2', 'DOC3'])
        self.assertEqual(len(bills), 2)
        self.assertEqual(self.env['account.move'].search(action['domain']), bills)
        invoice = bills.filtered(lambda b: b.ref == 'IV-DOC1')
        credit_note = bills.filtered(lambda b: b.ref == 'IV-DOC2')
        new_supplier = self.env['res.partner'].search([('vat', '=', 'C9999999999')])
        self.assertRecordValues(new_supplier, [{'name': 'New Supplier', 'is_company': True}])
        self.assertRecordValues(invoice + credit_note, [
            {
                'move_type': 'in_invoice',
                'state': 'draft',
                'partner_id': self.partner_a.id,
                'invoice_date': date(2024, 7, 10),
                'amount_total': 1000.0,
                'l10n_my_edi_state': 'received',
                'l10n_my_edi_document_type': '01',
                'l10n_my_edi_validation_time': datetime(2024, 7, 10, 2, 5),
            },
            {
                'move_type': 'in_refund',
                'state': 'draft',
                'partner_id': new_supplier.id,
                'invoice_date': date(2024, 7, 11),
                'amount_total': 50.0,
                'l10n_my_edi_state': 'received',
                'l10n_my_edi_document_type': '02',
                'l10n_my_edi_validation_time': datetime(2024, 7, 10, 2, 5),
            },
        ])
        self.assertRecordValues(invoice.invoice_line_ids, [{'quantity': 1.0, 'price_unit': 1000.0, 'tax_ids': []}])
        self.assertRecordValues(invoice.l10n_my_edi_received_document_id, [{
            'name': 'IV-DOC1',
            'myinvois_submission_uid': 'SUB-DOC1',
            'myinvois_document_long_id': 'LONG-DOC1',
        }])

    @freeze_time('2024-07-15 10:00:00')
    def test_sync_current_month_until_now(self):
        """ MyInvois refuses searches that end in the future. """
        _action, calls = self._sync([[]])
        self.assertEqual(calls[0]['date_to'], '2024-07-15T10:00:00+00:00')

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_all_pages(self):
        # DOC1 shifted to the second page as MyInvois received a new document while we were paging.
        _action, calls = self._sync([[self._document_data('DOC1')], [self._document_data('DOC1'), self._document_data('DOC2')]])
        self.assertEqual([call['page'] for call in calls], [1, 2])
        self.assertEqual(len(self._get_received_bills(['DOC1', 'DOC2'])), 2)

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_again(self):
        """ Syncing a month again only imports the new documents, and reflects the cancellations of the supplier. """
        self._sync([[self._document_data('DOC1'), self._document_data('DOC2'), self._document_data('DOC4')]])
        bills = self._get_received_bills(['DOC1', 'DOC2', 'DOC4'])
        bills.filtered(lambda b: b.ref == 'IV-DOC4').action_post()

        action, _calls = self._sync([[
            self._document_data('DOC1'),
            self._document_data('DOC2', status='cancelled'),
            # A posted bill may be paid already: it is left to the user.
            self._document_data('DOC4', status='cancelled'),
            # Cancelled before we ever saw it: there is nothing to pay.
            self._document_data('DOC3', status='cancelled'),
        ]])

        self.assertEqual(action['tag'], 'display_notification')
        self.assertEqual(self._get_received_bills(['DOC1', 'DOC2', 'DOC3', 'DOC4']), bills)
        self.assertRecordValues(bills.sorted('ref'), [
            {'ref': 'IV-DOC1', 'state': 'draft', 'l10n_my_edi_state': 'received'},
            {'ref': 'IV-DOC2', 'state': 'cancel', 'l10n_my_edi_state': 'cancelled'},
            {'ref': 'IV-DOC4', 'state': 'posted', 'l10n_my_edi_state': 'cancelled'},
        ])

    @freeze_time('2024-08-15 10:00:00')
    def test_received_bill_is_not_sent_to_myinvois(self):
        """ The supplier already issued the e-invoice: sending the bill would issue a self-billed invoice. """
        self._sync([[self._document_data('DOC1')]])
        bill = self._get_received_bills(['DOC1'])
        bill.action_post()

        self.assertFalse(bill.l10n_my_edi_is_applicable)
        with patch(CONTACT_PROXY_METHOD) as mock_contact_proxy:
            bill.action_l10n_my_edi_send_invoice()
        mock_contact_proxy.assert_not_called()
        self.assertEqual(bill.l10n_my_edi_document_ids, bill.l10n_my_edi_received_document_id)

    @freeze_time('2024-08-15 10:00:00')
    def test_post_received_bill_total(self):
        """ The line of a received bill can be split, as long as the bill still matches the e-invoice. """
        self._sync([[self._document_data('DOC1')]])
        bill = self._get_received_bills(['DOC1'])
        bill.invoice_line_ids.price_unit = 600.0
        with self.assertRaisesRegex(UserError, 'no longer matches the e-invoice'):
            bill.action_post()

        bill.invoice_line_ids = [Command.create({'name': 'Delivery', 'quantity': 1, 'price_unit': 400.0, 'tax_ids': []})]
        bill.action_post()
        self.assertEqual(bill.state, 'posted')

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_uses_the_company_of_the_journal(self):
        """ The documents synced are the ones of the company the bills are created in. """
        wizard = self.env['myinvois.document.sync.wizard'].create({
            'month': '2024-07-01',
            'journal_id': self.other_company_data['default_journal_purchase'].id,
        })
        with (
            patch(CONTACT_PROXY_METHOD) as mock_contact_proxy,
            self.assertRaisesRegex(UserError, 'register for the E-Invoicing service'),
        ):
            wizard.button_sync()
        mock_contact_proxy.assert_not_called()

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_error(self):
        wizard = self.env['myinvois.document.sync.wizard'].create({
            'month': '2024-07-01',
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        with (
            patch(CONTACT_PROXY_METHOD, return_value={'error': {'reference': 'search_too_frequent'}}),
            self.assertRaisesRegex(UserError, 'one search every 5 seconds'),
        ):
            wizard.button_sync()
