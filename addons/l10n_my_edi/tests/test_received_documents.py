# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import file_open

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
            'total': 1100.0,
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

    def _get_documents(self, uuids):
        return self.env['myinvois.document'].search([('myinvois_external_uuid', 'in', uuids)])

    def _get_received_bills(self, uuids):
        return self._get_documents(uuids).invoice_ids

    def _document_file(self, document):
        """ The document as MyInvois validated it: an invoice of 2 chairs at 500.00 with 10% sales tax. """
        with file_open('l10n_my_edi/tests/received_documents/invoice.xml') as file:
            return file.read().format(
                reference=document.name,
                type_code=document.myinvois_document_type,
                supplier_tin=document.myinvois_supplier_tin,
                supplier_name=document.myinvois_supplier_name,
            )

    def _create_bills(self, uuids, files=None):
        """ Create the bills of the received documents, the proxy returning their files (built from the template
        unless given).

        :return: the action returned and the uuids of the documents fetched from the proxy.
        """
        documents = self._get_documents(uuids)
        files = files or {document.myinvois_external_uuid: self._document_file(document) for document in documents}
        files = {uuid: file if isinstance(file, dict) else {'document': file} for uuid, file in files.items()}
        fetched_uuids = []

        def mock_contact_proxy(proxy_user, endpoint, params):
            self.assertEqual(endpoint, 'api/l10n_my_edi/1/get_document_file')
            fetched_uuids.append(params['document_uuid'])
            return files[params['document_uuid']]

        with patch(CONTACT_PROXY_METHOD, new=mock_contact_proxy):
            action = documents.action_create_received_bills()
        return action, fetched_uuids

    @freeze_time('2024-08-15 10:00:00')
    def test_received_number_does_not_change_own_sequence(self):
        self._sync([[self._document_data('DOC1', internal_id='INV/2024/00147')]])
        document = self.env['myinvois.document'].create({
            'company_id': self.company_data['company'].id,
            'currency_id': self.env.ref('base.MYR').id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'move_type': 'in_invoice',
            'myinvois_issuance_date': '2024-07-11',
        })
        self.assertEqual(document.name, document._get_starting_sequence()[:-5] + '00001')

    @freeze_time('2024-08-15 10:00:00')
    def test_own_sequence_continues_with_null_received_flag(self):
        values = {
            'company_id': self.company_data['company'].id,
            'currency_id': self.env.ref('base.MYR').id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'move_type': 'in_invoice',
            'myinvois_issuance_date': '2024-07-10',
        }
        predecessor = self.env['myinvois.document'].create({
            **values,
            'name': 'CPUR/2024/00147',
        })
        predecessor.flush_recordset()
        # Existing rows have NULL when the optional received flag is added at module upgrade.
        self.env.cr.execute('UPDATE myinvois_document SET is_received_document = NULL WHERE id = %s', [predecessor.id])
        predecessor.invalidate_recordset(['is_received_document'])
        self._sync([[self._document_data('DOC1', internal_id='INV/2024/00999')]])
        document = self.env['myinvois.document'].create({**values, 'myinvois_issuance_date': '2024-07-11'})
        self.assertEqual(document.name, 'CPUR/2024/00148')

    @freeze_time('2024-08-15 10:00:00')
    def test_received_document_cannot_be_deleted(self):
        self._sync([[self._document_data('DOC1')]])
        document = self._get_documents(['DOC1'])
        for state in ('received', 'cancelled'):
            document.myinvois_state = state
            with self.assertRaisesRegex(UserError, 'Archive it instead'):
                document.unlink()
        document.action_archive()
        self.assertFalse(document.active)

    @freeze_time('2024-08-15 10:00:00')
    def test_supplier_vat_does_not_override_malaysian_tin(self):
        self.partner_a.l10n_my_edi_malaysian_tin = 'C9999999999'
        self._sync([[self._document_data('DOC1')]])
        self._create_bills(['DOC1'])
        supplier = self._get_received_bills(['DOC1']).partner_id
        self.assertNotEqual(supplier, self.partner_a)
        self.assertEqual(supplier._l10n_my_edi_get_tin_for_myinvois(), 'C2584563201')

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_shorter_window(self):
        wizard = self.env['myinvois.document.sync.wizard'].create({
            'month': '2024-07-01',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'date_from': '2024-07-10',
            'date_to': '2024-07-11',
        })
        with patch(CONTACT_PROXY_METHOD, return_value={'documents': [], 'page_count': 1}) as mock:
            wizard.button_sync()
        self.assertEqual(mock.call_args.kwargs['params'], {
            'date_from': '2024-07-10T00:00:00+08:00',
            'date_to': '2024-07-11T23:59:59+08:00',
            'page': 1,
        })
        for start, end in [('2024-07-11', '2024-07-10'), ('2024-06-30', '2024-07-01'), ('2024-07-31', '2024-08-01')]:
            wizard.write({'date_from': start, 'date_to': end})
            with patch(CONTACT_PROXY_METHOD) as mock, self.assertRaisesRegex(UserError, 'within the selected month'):
                wizard.button_sync()
            mock.assert_not_called()

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_lists_received_documents(self):
        """ The sync lists the new valid documents for the user to create the bills of the ones they expect. """
        partner_count = self.env['res.partner'].search_count([])
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
        documents = self._get_documents(['DOC1', 'DOC2', 'DOC3'])
        self.assertEqual(self.env['myinvois.document'].search([('journal_id', '=', action['params']['next']['context']['journal_id'])]), documents)
        self.assertRecordValues(documents.sorted('name'), [
            {
                'name': 'IV-DOC1',
                'move_type': 'in_invoice',
                'myinvois_supplier_tin': 'C2584563201',
                'myinvois_issuance_date': date(2024, 7, 10),
                'myinvois_validation_time': datetime(2024, 7, 10, 2, 5),
                'myinvois_amount_total': 1100.0,
                'myinvois_submission_uid': 'SUB-DOC1',
                'myinvois_document_long_id': 'LONG-DOC1',
                'invoice_ids': [],
            },
            {
                'name': 'IV-DOC2',
                'move_type': 'in_refund',
                'myinvois_supplier_tin': 'C9999999999',
                'myinvois_issuance_date': date(2024, 7, 11),
                'myinvois_validation_time': datetime(2024, 7, 10, 2, 5),
                'myinvois_amount_total': 50.0,
                'myinvois_submission_uid': 'SUB-DOC2',
                'myinvois_document_long_id': 'LONG-DOC2',
                'invoice_ids': [],
            },
        ])
        self.assertEqual(self.env['res.partner'].search_count([]), partner_count)

    @freeze_time('2024-08-15 10:00:00')
    def test_create_bills(self):
        """ Each bill is imported from the document as MyInvois validated it, with its lines and taxes. The supplier
        is found by its TIN, or created if it is not in Odoo yet.
        """
        self._sync([[
            self._document_data('DOC1'),
            self._document_data('DOC2', document_type='02', supplier_tin='C9999999999', supplier_name='New Supplier'),
        ]])
        partner_count = self.env['res.partner'].search_count([])

        action, fetched_uuids = self._create_bills(['DOC1', 'DOC2'])

        self.assertEqual(sorted(fetched_uuids), ['DOC1', 'DOC2'])
        bills = self._get_received_bills(['DOC1', 'DOC2']).sorted('ref')
        self.assertEqual(self.env['account.move'].search(action['domain']), bills)
        new_supplier = self.env['res.partner'].search([('vat', '=', 'C9999999999')])
        self.assertRecordValues(new_supplier, [{'name': 'New Supplier', 'is_company': True}])
        self.assertEqual(self.env['res.partner'].search_count([]), partner_count + 1)
        self.assertRecordValues(bills, [
            {
                'move_type': 'in_invoice',
                'state': 'draft',
                'partner_id': self.partner_a.id,
                'ref': 'IV-DOC1',
                'invoice_date': date(2024, 7, 10),
                'amount_total': 1100.0,
                'l10n_my_edi_state': 'received',
                'l10n_my_edi_validation_time': datetime(2024, 7, 10, 2, 5),
            },
            {
                'move_type': 'in_refund',
                'state': 'draft',
                'partner_id': new_supplier.id,
                'ref': 'IV-DOC2',
                'invoice_date': date(2024, 7, 10),
                'amount_total': 1100.0,
                'l10n_my_edi_state': 'received',
                'l10n_my_edi_validation_time': datetime(2024, 7, 10, 2, 5),
            },
        ])
        tax_10 = self.env['account.chart.template'].ref('l10n_my_tax_purchase_10')
        self.assertRecordValues(bills.invoice_line_ids, [
            {'name': 'Chairs', 'quantity': 2.0, 'price_unit': 500.0, 'tax_ids': tax_10.ids, 'balance': 1000.0},
            {'name': 'Chairs', 'quantity': 2.0, 'price_unit': 500.0, 'tax_ids': tax_10.ids, 'balance': -1000.0},
        ])

    @freeze_time('2024-08-15 10:00:00')
    def test_create_bill_from_json_document(self):
        """ A document submitted to MyInvois in JSON is the same UBL: its bill gets its lines and taxes all the same. """
        self._sync([[self._document_data('DOC1')]])
        with file_open('l10n_my_edi/tests/received_documents/invoice.json') as file:
            self._create_bills(['DOC1'], files={'DOC1': file.read()})

        bill = self._get_received_bills(['DOC1'])
        self.assertRecordValues(bill, [{'partner_id': self.partner_a.id, 'ref': 'IV-DOC1', 'invoice_date': date(2024, 7, 10), 'amount_total': 1100.0}])
        tax_10 = self.env['account.chart.template'].ref('l10n_my_tax_purchase_10')
        self.assertRecordValues(bill.invoice_line_ids, [{'name': 'Chairs', 'quantity': 2.0, 'price_unit': 500.0, 'tax_ids': tax_10.ids}])

    @freeze_time('2024-08-15 10:00:00')
    def test_create_bills_error(self):
        """ A document MyInvois refuses to give gets no bill, for the user to try again. """
        self._sync([[self._document_data('DOC1'), self._document_data('DOC2')]])
        files = {document.myinvois_external_uuid: self._document_file(document) for document in self._get_documents(['DOC1'])}
        files['DOC2'] = {'error': {'reference': 'rate_limit_exceeded'}}
        with self.assertRaisesRegex(UserError, 'request limit has been reached'):
            self._create_bills(['DOC1', 'DOC2'], files=files)
        self.assertFalse(self.env['account.move'].search([('ref', '=', 'IV-DOC2')]))

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
        self.assertEqual(len(self._get_documents(['DOC1', 'DOC2'])), 2)

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_again(self):
        """ Syncing a month again only imports the new documents, and reflects the cancellations of the supplier. """
        self._sync([[self._document_data('DOC1'), self._document_data('DOC2'), self._document_data('DOC4')]])
        self._create_bills(['DOC1', 'DOC2', 'DOC4'])
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
    def test_sync_again_archived_document(self):
        self._sync([[self._document_data('DOC1')]])
        document = self._get_documents(['DOC1'])
        document.action_archive()

        self._sync([[self._document_data('DOC1')]])
        self.assertFalse(self._get_documents(['DOC1']))
        self.assertEqual(self.env['myinvois.document'].with_context(active_test=False).search([('myinvois_external_uuid', '=', 'DOC1')]), document)

    @freeze_time('2024-08-15 10:00:00')
    def test_sync_in_branch(self):
        """ Branches share the TIN of their parent: a document imported by one is not imported again by the other,
        even for a user who does not have the other one enabled.
        """
        parent = self.company_data['company']
        branch = self.env['res.company'].create({
            'name': 'MY Branch Company',
            'parent_id': parent.id,
            'country_id': self.env.ref('base.my').id,
            'account_fiscal_country_id': self.env.ref('base.my').id,
            'vat': parent.vat,
        })
        branch_journal = self.env['account.journal'].create({
            'name': 'Branch Purchases',
            'code': 'BPUR',
            'type': 'purchase',
            'company_id': branch.id,
        })
        self._sync([[self._document_data('DOC1')]])

        branch_user = new_test_user(
            self.env, login='branch_user', groups='account.group_account_invoice',
            company_id=branch.id, company_ids=[Command.set((parent + branch).ids)],
        )
        wizard = self.env['myinvois.document.sync.wizard'].with_user(branch_user).with_context(allowed_company_ids=branch.ids).create({
            'month': '2024-07-01',
            'journal_id': branch_journal.id,
        })
        with patch(CONTACT_PROXY_METHOD, return_value={'documents': [self._document_data('DOC1')], 'page_count': 1}):
            action = wizard.button_sync()
        self.assertEqual(action['params']['message'], 'No new document was received on MyInvois for the selected dates.')
        self.assertFalse(self.env['myinvois.document'].search([('journal_id', '=', branch_journal.id)]))

    @freeze_time('2024-08-15 10:00:00')
    def test_create_bills_links_bill_entered_by_user(self):
        """ A bill the user entered already, for the same supplier and reference, gets the document instead of a new one. """
        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'ref': 'IV-DOC1',
            'invoice_date': '2024-07-10',
            'invoice_line_ids': [Command.create({'name': 'Chairs', 'quantity': 1, 'price_unit': 1000.0, 'tax_ids': []})],
        }
        entered_bill, other_supplier_bill = self.env['account.move'].create([bill_vals, {**bill_vals, 'partner_id': self.partner_b.id}])

        self._sync([[self._document_data('DOC1')]])
        action, fetched_uuids = self._create_bills(['DOC1'])

        self.assertFalse(fetched_uuids)
        self.assertEqual(self._get_received_bills(['DOC1']), entered_bill)
        self.assertEqual(self.env['account.move'].search(action['domain']), entered_bill)
        self.assertRecordValues(entered_bill + other_supplier_bill, [
            {'l10n_my_edi_state': 'received', 'invoice_line_ids': entered_bill.invoice_line_ids.ids},
            {'l10n_my_edi_state': False, 'invoice_line_ids': other_supplier_bill.invoice_line_ids.ids},
        ])

    @freeze_time('2024-08-15 10:00:00')
    def test_create_bills_supplier_malaysian_tin_first(self):
        """ The Malaysian TIN of a partner is the one used on MyInvois; its Tax ID only when it has none. """
        self.partner_b.l10n_my_edi_malaysian_tin = self.partner_a.vat
        self._sync([[self._document_data('DOC1', supplier_tin=self.partner_a.vat)]])
        self._create_bills(['DOC1'])
        self.assertEqual(self._get_received_bills(['DOC1']).partner_id, self.partner_b)

    @freeze_time('2024-08-15 10:00:00')
    def test_received_bill_is_not_sent_to_myinvois(self):
        """ The supplier already issued the e-invoice: sending the bill would issue a self-billed invoice. """
        self._sync([[self._document_data('DOC1')]])
        self._create_bills(['DOC1'])
        bill = self._get_received_bills(['DOC1'])
        bill.action_post()

        self.assertFalse(bill.l10n_my_edi_is_applicable)
        with patch(CONTACT_PROXY_METHOD) as mock_contact_proxy:
            bill.action_l10n_my_edi_send_invoice()
        mock_contact_proxy.assert_not_called()
        self.assertEqual(bill.l10n_my_edi_document_ids, bill.l10n_my_edi_received_document_id)

    @freeze_time('2024-08-15 10:00:00')
    def test_post_received_bill_total(self):
        """ The lines of a received bill can be changed, as long as the bill still matches the e-invoice. """
        self._sync([[self._document_data('DOC1')]])
        self._create_bills(['DOC1'])
        bill = self._get_received_bills(['DOC1'])
        bill.invoice_line_ids.quantity = 1.0
        with self.assertRaisesRegex(UserError, 'no longer matches the e-invoice'):
            bill.action_post()

        bill.invoice_line_ids = [Command.create({'name': 'Delivery', 'quantity': 1, 'price_unit': 500.0, 'tax_ids': bill.invoice_line_ids.tax_ids.ids})]
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

    def test_post_received_bill_total_in_other_company_currency(self):
        """ The total of the e-invoice is in MYR, even for a company keeping its books in another currency. """
        company_data = self.other_company_data
        myr = self.env.ref('base.MYR')
        self.env['res.currency.rate'].create({'name': '2024-01-01', 'rate': 4.0, 'currency_id': myr.id, 'company_id': company_data['company'].id})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': company_data['default_journal_purchase'].id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-07-10',
            'currency_id': myr.id,
            'invoice_line_ids': [Command.create({'name': 'IV-DOC1', 'quantity': 1, 'price_unit': 1000.0, 'tax_ids': []})],
        })
        self.env['myinvois.document'].create({
            'name': 'IV-DOC1',
            'company_id': company_data['company'].id,
            'currency_id': myr.id,
            'journal_id': company_data['default_journal_purchase'].id,
            'move_type': 'in_invoice',
            'is_received_document': True,
            'myinvois_state': 'received',
            'myinvois_amount_total': 1000.0,
            'myinvois_external_uuid': 'DOC1',
            'invoice_ids': [Command.link(bill.id)],
        })
        bill.action_post()
        self.assertEqual(bill.state, 'posted')

    @freeze_time('2024-08-15 10:00:00')
    def test_received_bill_type_is_the_document_type(self):
        self._sync([[self._document_data('DOC1')]])
        self._create_bills(['DOC1'])
        bill = self._get_received_bills(['DOC1'])
        with self.assertRaisesRegex(UserError, 'cannot be changed'):
            bill.action_switch_move_type()

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
