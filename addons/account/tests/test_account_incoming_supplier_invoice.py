# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

from contextlib import contextmanager
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountIncomingSupplierInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.internal_user = cls.env['res.users'].create({
            'name': 'Internal User',
            'login': 'internal.user@test.odoo.com',
            'email': 'internal.user@test.odoo.com',
        })

        cls.supplier_partner = cls.env['res.partner'].create({
            'name': 'Your Supplier',
            'email': 'supplier@other.company.com',
            'supplier_rank': 10,
        })

        cls.journal = cls.company_data['default_journal_purchase']
        cls.attachment_number = 0

    def _create_dummy_pdf_attachment(self):
        self.attachment_number += 1
        rawpdf_base64 = 'JVBERi0xLjYNJeLjz9MNCjI0IDAgb2JqDTw8L0ZpbHRlci9GbGF0ZURlY29kZS9GaXJzdCA0L0xlbmd0aCAyMTYvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjePI9RS8MwFIX/yn1bi9jepCQ6GYNpFBTEMsW97CVLbjWYNpImmz/fVsXXcw/f/c4SEFarepPTe4iFok8dU09DgtDBQx6TMwT74vaLTE7uSPDUdXM0Xe/73r1FnVwYYEtHR6d9WdY3kX4ipRMV6oojSmxQMoGyac5RLBAXf63p38aGA7XPorLewyvFcYaJile8rB+D/YcwiRdMMGScszO8/IW0MdhsaKKYGA46gXKTr/cUQVY4We/cYMNpnLVeXPJUXHs9fECr7kAFk+eZ5Xr9LcAAfKpQrA0KZW5kc3RyZWFtDWVuZG9iag0yNSAwIG9iag08PC9GaWx0ZXIvRmxhdGVEZWNvZGUvRmlyc3QgNC9MZW5ndGggNDkvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjeslAwULCx0XfOL80rUTDU985MKY42NAIKBsXqh1QWpOoHJKanFtvZAQQYAN/6C60NCmVuZHN0cmVhbQ1lbmRvYmoNMjYgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDkvTGVuZ3RoIDQyL04gMi9UeXBlL09ialN0bT4+c3RyZWFtDQpo3jJTMFAwVzC0ULCx0fcrzS2OBnENFIJi7eyAIsH6LnZ2AAEGAI2FCDcNCmVuZHN0cmVhbQ1lbmRvYmoNMjcgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDUvTGVuZ3RoIDEyMC9OIDEvVHlwZS9PYmpTdG0+PnN0cmVhbQ0KaN4yNFIwULCx0XfOzytJzSspVjAyBgoE6TsX5Rc45VdEGwB5ZoZGCuaWRrH6vqkpmYkYogGJRUCdChZgfUGpxfmlRcmpxUAzA4ryk4NTS6L1A1zc9ENSK0pi7ez0g/JLEktSFQz0QyoLUoF601Pt7AACDADYoCeWDQplbmRzdHJlYW0NZW5kb2JqDTIgMCBvYmoNPDwvTGVuZ3RoIDM1MjUvU3VidHlwZS9YTUwvVHlwZS9NZXRhZGF0YT4+c3RyZWFtDQo8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjQtYzAwNSA3OC4xNDczMjYsIDIwMTIvMDgvMjMtMTM6MDM6MDMgICAgICAgICI+CiAgIDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnBkZj0iaHR0cDovL25zLmFkb2JlLmNvbS9wZGYvMS4zLyIKICAgICAgICAgICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICAgICAgICAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgICAgICAgICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIj4KICAgICAgICAgPHBkZjpQcm9kdWNlcj5BY3JvYmF0IERpc3RpbGxlciA2LjAgKFdpbmRvd3MpPC9wZGY6UHJvZHVjZXI+CiAgICAgICAgIDx4bXA6Q3JlYXRlRGF0ZT4yMDA2LTAzLTA2VDE1OjA2OjMzLTA1OjAwPC94bXA6Q3JlYXRlRGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdG9yVG9vbD5BZG9iZVBTNS5kbGwgVmVyc2lvbiA1LjIuMjwveG1wOkNyZWF0b3JUb29sPgogICAgICAgICA8eG1wOk1vZGlmeURhdGU+MjAxNi0wNy0xNVQxMDoxMjoyMSswODowMDwveG1wOk1vZGlmeURhdGU+CiAgICAgICAgIDx4bXA6TWV0YWRhdGFEYXRlPjIwMTYtMDctMTVUMTA6MTI6MjErMDg6MDA8L3htcDpNZXRhZGF0YURhdGU+CiAgICAgICAgIDx4bXBNTTpEb2N1bWVudElEPnV1aWQ6ZmYzZGNmZDEtMjNmYS00NzZmLTgzOWEtM2U1Y2FlMmRhMmViPC94bXBNTTpEb2N1bWVudElEPgogICAgICAgICA8eG1wTU06SW5zdGFuY2VJRD51dWlkOjM1OTM1MGIzLWFmNDAtNGQ4YS05ZDZjLTAzMTg2YjRmZmIzNjwveG1wTU06SW5zdGFuY2VJRD4KICAgICAgICAgPGRjOmZvcm1hdD5hcHBsaWNhdGlvbi9wZGY8L2RjOmZvcm1hdD4KICAgICAgICAgPGRjOnRpdGxlPgogICAgICAgICAgICA8cmRmOkFsdD4KICAgICAgICAgICAgICAgPHJkZjpsaSB4bWw6bGFuZz0ieC1kZWZhdWx0Ij5CbGFuayBQREYgRG9jdW1lbnQ8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6QWx0PgogICAgICAgICA8L2RjOnRpdGxlPgogICAgICAgICA8ZGM6Y3JlYXRvcj4KICAgICAgICAgICAgPHJkZjpTZXE+CiAgICAgICAgICAgICAgIDxyZGY6bGk+RGVwYXJ0bWVudCBvZiBKdXN0aWNlIChFeGVjdXRpdmUgT2ZmaWNlIG9mIEltbWlncmF0aW9uIFJldmlldyk8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6U2VxPgogICAgICAgICA8L2RjOmNyZWF0b3I+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgog' + 682*'ICAg' + 'Cjw/eHBhY2tldCBlbmQ9InciPz4NCmVuZHN0cmVhbQ1lbmRvYmoNMTEgMCBvYmoNPDwvTWV0YWRhdGEgMiAwIFIvUGFnZUxhYmVscyA2IDAgUi9QYWdlcyA4IDAgUi9UeXBlL0NhdGFsb2c+Pg1lbmRvYmoNMjMgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0xlbmd0aCAxMD4+c3RyZWFtDQpIiQIIMAAAAAABDQplbmRzdHJlYW0NZW5kb2JqDTI4IDAgb2JqDTw8L0RlY29kZVBhcm1zPDwvQ29sdW1ucyA0L1ByZWRpY3RvciAxMj4+L0ZpbHRlci9GbGF0ZURlY29kZS9JRFs8REI3Nzc1Q0NFMjI3RjZCMzBDNDQwREY0MjIxREMzOTA+PEJGQ0NDRjNGNTdGNjEzNEFCRDNDMDRBOUU0Q0ExMDZFPl0vSW5mbyA5IDAgUi9MZW5ndGggODAvUm9vdCAxMSAwIFIvU2l6ZSAyOS9UeXBlL1hSZWYvV1sxIDIgMV0+PnN0cmVhbQ0KaN5iYgACJjDByGzIwPT/73koF0wwMUiBWYxA4v9/EMHA9I/hBVCxoDOQeH8DxH2KrIMIglFwIpD1vh5IMJqBxPpArHYgwd/KABBgAP8bEC0NCmVuZHN0cmVhbQ1lbmRvYmoNc3RhcnR4cmVmDQo0NTc2DQolJUVPRg0K'
        return self.env['ir.attachment'].create({
            'name': f"attachment_{self.attachment_number}",
            'datas': rawpdf_base64,
            'type': 'binary',
            'mimetype': 'application/pdf',
        })

    def _create_dummy_xml_attachment(self):
        self.attachment_number += 1
        return self.env['ir.attachment'].create({
            'name': f"attachment_{self.attachment_number}",
            'raw': '<test/>',
            'mimetype': 'application/xml',
        })

    def _create_dummy_gif_attachment(self):
        self.attachment_number += 1
        return self.env['ir.attachment'].create({
            'name': f"attachment_{self.attachment_number}",
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'mimetype': 'image/gif',
        })

    @contextmanager
    def with_success_decoder(self, omit=None):
        decoded_files = set()

        def get_edi_decoder(_record, file_data, new=False):

            def decoder(*args, **kwargs):
                return not omit or file_data['attachment'].name not in omit

            if decoder():
                decoded_files.add(file_data['filename'])
            return decoder

        with patch.object(type(self.env['account.move']), '_get_edi_decoder', get_edi_decoder):
            yield decoded_files

    @contextmanager
    def with_simulated_embedded_xml(self, pdf):
        super_decode_edi_pdf = type(self.env['ir.attachment'])._decode_edi_pdf
        xml_filename = f"{pdf.name}_xml"

        def decode_edi_pdf(record, filename, content):
            results = super_decode_edi_pdf(record, filename, content)
            if filename == pdf.name:
                embedded_files = self.env['ir.attachment']._decode_edi_xml(xml_filename, '<test></test>')
                for file_data in embedded_files:
                    file_data['sort_weight'] += 1
                    file_data['originator_pdf'] = pdf
                results += embedded_files
            return results

        with patch.object(type(self.env['ir.attachment']), '_decode_edi_pdf', decode_edi_pdf):
            yield xml_filename

    def _assert_extend_with_attachments(self, expected_values, new=False):
        attachments = self.env['ir.attachment'].browse([x.id for x in expected_values])
        nb_moves_before = self.env['account.move'].search_count([('company_id', '=', self.env.company.id)])
        results = self.env['account.move']\
            .with_context(default_move_type='out_invoice', default_journal_id=self.company_data['default_journal_sale'].id)\
            ._extend_with_attachments(attachments, new=new)
        invoice_number = 0
        previous_invoice = None
        current_values = {}
        for attachment, invoice in results.items():
            if previous_invoice != invoice:
                invoice_number += 1
                previous_invoice = invoice

            current_values[attachment.name] = invoice_number

        self.assertEqual(current_values, {k.name: v for k, v in expected_values.items()})

        nb_moves_after = self.env['account.move'].search_count([('company_id', '=', self.env.company.id)])
        self.assertEqual(nb_moves_before + invoice_number, nb_moves_after)

    def test_supplier_invoice_mailed_from_supplier(self):
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.supplier_partner.name, self.supplier_partner.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "You know, that thing that you bought.",
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        following_partners = invoice.message_follower_ids.mapped('partner_id')
        self.assertEqual(following_partners, self.env.user.partner_id)
        self.assertRegex(invoice.name, 'BILL/\d{4}/\d{2}/0001')

    def test_supplier_invoice_forwarded_by_internal_user_without_supplier(self):
        """ In this test, the bill was forwarded by an employee,
            but no partner email address is found in the body."""
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.internal_user.name, self.internal_user.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "You know, that thing that you bought.",
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        following_partners = invoice.message_follower_ids.mapped('partner_id')
        self.assertEqual(following_partners, self.env.user.partner_id | self.internal_user.partner_id)

    def test_supplier_invoice_forwarded_by_internal_with_supplier_in_body(self):
        """ In this test, the bill was forwarded by an employee,
            and the partner email address is found in the body."""
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.internal_user.name, self.internal_user.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "Mail sent by %s <%s>:\nYou know, that thing that you bought." % (self.supplier_partner.name, self.supplier_partner.email),
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        following_partners = invoice.message_follower_ids.mapped('partner_id')
        self.assertEqual(following_partners, self.env.user.partner_id | self.internal_user.partner_id)

    def test_supplier_invoice_forwarded_by_internal_with_internal_in_body(self):
        """ In this test, the bill was forwarded by an employee,
            and the internal user email address is found in the body."""
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.internal_user.name, self.internal_user.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "Mail sent by %s <%s>:\nYou know, that thing that you bought." % (self.internal_user.name, self.internal_user.email),
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        following_partners = invoice.message_follower_ids.mapped('partner_id')
        self.assertEqual(following_partners, self.env.user.partner_id | self.internal_user.partner_id)

    def test_extend_with_attachments_multi_pdf(self):
        pdf1 = self._create_dummy_pdf_attachment()
        pdf2 = self._create_dummy_pdf_attachment()
        gif1 = self._create_dummy_gif_attachment()
        gif2 = self._create_dummy_gif_attachment()
        xml1 = self._create_dummy_xml_attachment()
        xml2 = self._create_dummy_xml_attachment()
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 1}, new=False)
            self.assertEqual(decoded_files, {pdf1.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 2}, new=True)
            self.assertEqual(decoded_files, {pdf1.name, pdf2.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 1, gif1: 1, gif2: 1}, new=False)
            self.assertEqual(decoded_files, {pdf1.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 2, gif1: 3, gif2: 4}, new=True)
            self.assertEqual(decoded_files, {pdf1.name, pdf2.name, gif1.name, gif2.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, xml1: 1}, new=False)
            self.assertEqual(decoded_files, {xml1.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, xml1: 1}, new=True)
            self.assertEqual(decoded_files, {xml1.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({xml1: 1, xml2: 1}, new=False)
            self.assertEqual(decoded_files, {xml1.name})
        with self.with_success_decoder() as decoded_files:
            self._assert_extend_with_attachments({xml1: 1, xml2: 2}, new=True)
            self.assertEqual(decoded_files, {xml1.name, xml2.name})
        with self.with_success_decoder(omit={pdf1.name}) as decoded_files:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 2}, new=True)
            self.assertEqual(decoded_files, {pdf2.name})
        with self.with_success_decoder() as decoded_files, self.with_simulated_embedded_xml(pdf1) as xml_filename:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 1}, new=False)
            self.assertEqual(decoded_files, {xml_filename})
        with self.with_success_decoder() as decoded_files, self.with_simulated_embedded_xml(pdf1) as xml_filename:
            self._assert_extend_with_attachments({pdf1: 1, pdf2: 2}, new=True)
            self.assertEqual(decoded_files, {xml_filename, pdf2.name})
        with self.with_success_decoder() as decoded_files, self.with_simulated_embedded_xml(pdf1):
            self._assert_extend_with_attachments({pdf1: 1, xml1: 1}, new=False)
            self.assertEqual(decoded_files, {xml1.name})
        with self.with_success_decoder() as decoded_files, self.with_simulated_embedded_xml(pdf1):
            self._assert_extend_with_attachments({pdf1: 1, xml1: 1}, new=True)
            self.assertEqual(decoded_files, {xml1.name})
