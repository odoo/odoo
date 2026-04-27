# -*- coding: utf-8 -*-

import base64
from datetime import timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests import Form

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.documents.models.documents_document import Document
from odoo.tools.mimetypes import magic

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("workflow bridge account", 'utf-8'))
PDF = 'JVBERi0xLjYNJeLjz9MNCjI0IDAgb2JqDTw8L0ZpbHRlci9GbGF0ZURlY29kZS9GaXJzdCA0L0xlbmd0aCAyMTYvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjePI9RS8MwFIX/yn1bi9jepCQ6GYNpFBTEMsW97CVLbjWYNpImmz/fVsXXcw/f/c4SEFarepPTe4iFok8dU09DgtDBQx6TMwT74vaLTE7uSPDUdXM0Xe/73r1FnVwYYEtHR6d9WdY3kX4ipRMV6oojSmxQMoGyac5RLBAXf63p38aGA7XPorLewyvFcYaJile8rB+D/YcwiRdMMGScszO8/IW0MdhsaKKYGA46gXKTr/cUQVY4We/cYMNpnLVeXPJUXHs9fECr7kAFk+eZ5Xr9LcAAfKpQrA0KZW5kc3RyZWFtDWVuZG9iag0yNSAwIG9iag08PC9GaWx0ZXIvRmxhdGVEZWNvZGUvRmlyc3QgNC9MZW5ndGggNDkvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjeslAwULCx0XfOL80rUTDU985MKY42NAIKBsXqh1QWpOoHJKanFtvZAQQYAN/6C60NCmVuZHN0cmVhbQ1lbmRvYmoNMjYgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDkvTGVuZ3RoIDQyL04gMi9UeXBlL09ialN0bT4+c3RyZWFtDQpo3jJTMFAwVzC0ULCx0fcrzS2OBnENFIJi7eyAIsH6LnZ2AAEGAI2FCDcNCmVuZHN0cmVhbQ1lbmRvYmoNMjcgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDUvTGVuZ3RoIDEyMC9OIDEvVHlwZS9PYmpTdG0+PnN0cmVhbQ0KaN4yNFIwULCx0XfOzytJzSspVjAyBgoE6TsX5Rc45VdEGwB5ZoZGCuaWRrH6vqkpmYkYogGJRUCdChZgfUGpxfmlRcmpxUAzA4ryk4NTS6L1A1zc9ENSK0pi7ez0g/JLEktSFQz0QyoLUoF601Pt7AACDADYoCeWDQplbmRzdHJlYW0NZW5kb2JqDTIgMCBvYmoNPDwvTGVuZ3RoIDM1MjUvU3VidHlwZS9YTUwvVHlwZS9NZXRhZGF0YT4+c3RyZWFtDQo8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjQtYzAwNSA3OC4xNDczMjYsIDIwMTIvMDgvMjMtMTM6MDM6MDMgICAgICAgICI+CiAgIDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnBkZj0iaHR0cDovL25zLmFkb2JlLmNvbS9wZGYvMS4zLyIKICAgICAgICAgICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICAgICAgICAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgICAgICAgICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIj4KICAgICAgICAgPHBkZjpQcm9kdWNlcj5BY3JvYmF0IERpc3RpbGxlciA2LjAgKFdpbmRvd3MpPC9wZGY6UHJvZHVjZXI+CiAgICAgICAgIDx4bXA6Q3JlYXRlRGF0ZT4yMDA2LTAzLTA2VDE1OjA2OjMzLTA1OjAwPC94bXA6Q3JlYXRlRGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdG9yVG9vbD5BZG9iZVBTNS5kbGwgVmVyc2lvbiA1LjIuMjwveG1wOkNyZWF0b3JUb29sPgogICAgICAgICA8eG1wOk1vZGlmeURhdGU+MjAxNi0wNy0xNVQxMDoxMjoyMSswODowMDwveG1wOk1vZGlmeURhdGU+CiAgICAgICAgIDx4bXA6TWV0YWRhdGFEYXRlPjIwMTYtMDctMTVUMTA6MTI6MjErMDg6MDA8L3htcDpNZXRhZGF0YURhdGU+CiAgICAgICAgIDx4bXBNTTpEb2N1bWVudElEPnV1aWQ6ZmYzZGNmZDEtMjNmYS00NzZmLTgzOWEtM2U1Y2FlMmRhMmViPC94bXBNTTpEb2N1bWVudElEPgogICAgICAgICA8eG1wTU06SW5zdGFuY2VJRD51dWlkOjM1OTM1MGIzLWFmNDAtNGQ4YS05ZDZjLTAzMTg2YjRmZmIzNjwveG1wTU06SW5zdGFuY2VJRD4KICAgICAgICAgPGRjOmZvcm1hdD5hcHBsaWNhdGlvbi9wZGY8L2RjOmZvcm1hdD4KICAgICAgICAgPGRjOnRpdGxlPgogICAgICAgICAgICA8cmRmOkFsdD4KICAgICAgICAgICAgICAgPHJkZjpsaSB4bWw6bGFuZz0ieC1kZWZhdWx0Ij5CbGFuayBQREYgRG9jdW1lbnQ8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6QWx0PgogICAgICAgICA8L2RjOnRpdGxlPgogICAgICAgICA8ZGM6Y3JlYXRvcj4KICAgICAgICAgICAgPHJkZjpTZXE+CiAgICAgICAgICAgICAgIDxyZGY6bGk+RGVwYXJ0bWVudCBvZiBKdXN0aWNlIChFeGVjdXRpdmUgT2ZmaWNlIG9mIEltbWlncmF0aW9uIFJldmlldyk8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6U2VxPgogICAgICAgICA8L2RjOmNyZWF0b3I+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgog' + 682 * 'ICAg' + 'Cjw/eHBhY2tldCBlbmQ9InciPz4NCmVuZHN0cmVhbQ1lbmRvYmoNMTEgMCBvYmoNPDwvTWV0YWRhdGEgMiAwIFIvUGFnZUxhYmVscyA2IDAgUi9QYWdlcyA4IDAgUi9UeXBlL0NhdGFsb2c+Pg1lbmRvYmoNMjMgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0xlbmd0aCAxMD4+c3RyZWFtDQpIiQIIMAAAAAABDQplbmRzdHJlYW0NZW5kb2JqDTI4IDAgb2JqDTw8L0RlY29kZVBhcm1zPDwvQ29sdW1ucyA0L1ByZWRpY3RvciAxMj4+L0ZpbHRlci9GbGF0ZURlY29kZS9JRFs8REI3Nzc1Q0NFMjI3RjZCMzBDNDQwREY0MjIxREMzOTA+PEJGQ0NDRjNGNTdGNjEzNEFCRDNDMDRBOUU0Q0ExMDZFPl0vSW5mbyA5IDAgUi9MZW5ndGggODAvUm9vdCAxMSAwIFIvU2l6ZSAyOS9UeXBlL1hSZWYvV1sxIDIgMV0+PnN0cmVhbQ0KaN5iYgACJjDByGzIwPT/73koF0wwMUiBWYxA4v9/EMHA9I/hBVCxoDOQeH8DxH2KrIMIglFwIpD1vh5IMJqBxPpArHYgwd/KABBgAP8bEC0NCmVuZHN0cmVhbQ1lbmRvYmoNc3RhcnR4cmVmDQo0NTc2DQolJUVPRg0K'


@tagged('post_install', '-at_install', 'test_document_bridge')
class TestCaseDocumentsBridgeAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder_a = cls.env['documents.document'].create({
            'name': 'folder A',
            'type': 'folder',
        })
        cls.folder_a_a = cls.env['documents.document'].create({
            'name': 'folder A - A',
            'folder_id': cls.folder_a.id,
            'type': 'folder',
        })
        cls.document_txt = cls.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': cls.folder_a_a.id,
        })
        cls.document_gif = cls.env['documents.document'].create({
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': cls.folder_a.id,
        })

    def test_action_view_documents_account_move(self):
        """
        Test the behavior of opening default folder when there are more than one documents.
        """
        self.env.user.company_id.documents_account_settings = True
        account_move_test_1, account_move_test_2 = self.env['account.move'].create([{
            'name': 'Journal Entry 1',
            'move_type': 'entry',
        }, {
            'name': 'Journal Entry 2',
            'move_type': 'entry',
        }])
        self.env['documents.account.folder.setting'].create({
            'folder_id': self.folder_a.id,
            'journal_id': account_move_test_1.journal_id.id,
        })
        self.assertFalse(account_move_test_1.has_documents, "Should be False because no attachment is attached to this record")
        self.assertFalse(account_move_test_2.has_documents, "Should be False because no attachment is attached to this record")
        attachments = self.env['ir.attachment'].create([{
            'name': 'fileText_test.txt',
            'res_model': 'account.move',
            'res_id': account_move_test_1.id,
        }, {
            'name': 'fileText_test2.txt',
            'res_model': 'account.move',
            'res_id': account_move_test_1.id,
        }])
        self.assertTrue(account_move_test_1.has_documents, "Should be True because attachment is attached to this record")
        self.assertFalse(account_move_test_2.has_documents, "Should be False because no attachment is attached to this record")

        # If both the documents have same folder, open that folder.
        action = account_move_test_1.action_view_documents_account_move()
        self.assertEqual(action['context']['searchpanel_default_folder_id'], self.folder_a.id, "The 'folder A' should be the default.")

        # If both the documents have different folder, open the 'All' folder.
        folder_test = self.env['documents.document'].create({'name': 'folder_test', 'type': 'folder'})
        document = self.env['documents.document'].search([('attachment_id', '=', attachments[0].id)])
        document.folder_id = folder_test.id

        action = account_move_test_1.action_view_documents_account_move()
        self.assertFalse(action['context']['searchpanel_default_folder_id'], "The 'All' folder should be the default.")

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (vendor bill & credit note).

        """
        self.assertEqual(self.document_txt.res_model, 'documents.document', "failed at default res model")
        account_moves_count_pre = self.env['account.move'].sudo().search_count([])
        multi_return = (self.document_txt | self.document_gif).account_create_account_move('in_invoice')
        account_moves_count_post = self.env['account.move'].sudo().search_count([])
        self.assertEqual(account_moves_count_post - account_moves_count_pre, 2)
        self.assertEqual(multi_return.get('type'), 'ir.actions.act_window',
                         'failed at invoice workflow return value type')
        self.assertEqual(multi_return.get('res_model'), 'account.move',
                         'failed at invoice workflow return value res model')

        self.assertEqual(self.document_txt.res_model, 'account.move', "failed at workflow_bridge_dms_account"
                                                                           " new res_model")
        vendor_bill_txt = self.env['account.move'].search([('id', '=', self.document_txt.res_id)])
        self.assertTrue(vendor_bill_txt.exists(), 'failed at workflow_bridge_dms_account vendor_bill')
        self.assertEqual(self.document_txt.res_id, vendor_bill_txt.id, "failed at workflow_bridge_dms_account res_id")
        self.assertEqual(vendor_bill_txt.move_type, 'in_invoice', "failed at workflow_bridge_dms_account vendor_bill type")
        vendor_bill_gif = self.env['account.move'].search([('id', '=', self.document_gif.res_id)])
        self.assertEqual(self.document_gif.res_id, vendor_bill_gif.id, "failed at workflow_bridge_dms_account res_id")
        account_moves_count_pre = self.env['account.move'].sudo().search_count([])
        single_return = self.document_txt.account_create_account_move('in_invoice')
        account_moves_count_post = self.env['account.move'].sudo().search_count([])
        self.assertEqual(account_moves_count_post - account_moves_count_pre, 0)
        self.assertEqual(single_return.get('res_model'), 'account.move',
                         'failed at invoice res_model action from workflow create model')
        invoice = self.env[single_return['res_model']].browse(single_return.get('res_id'))
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', invoice.id)])
        self.assertEqual(len(attachments), 1, 'there should only be one ir attachment matching')

    def test_bridge_account_account_settings_on_write(self):
        """
        Makes sure the settings apply their values when an ir_attachment is set as message_main_attachment_id
        on invoices.
        """
        folder_test = self.env['documents.document'].create({'name': 'folder_test', 'type': 'folder'})
        self.env.user.company_id.documents_account_settings = True

        for invoice_type in ['in_invoice', 'out_invoice', 'in_refund', 'out_refund']:
            invoice_test = self.env['account.move'].with_context(default_move_type=invoice_type).create({
                'name': 'invoice_test',
                'move_type': invoice_type,
            })
            setting = self.env['documents.account.folder.setting'].create({
                'folder_id': folder_test.id,
                'journal_id': invoice_test.journal_id.id,
            })

            attachments = self.env["ir.attachment"]
            for i in range(3):
                attachment = self.env["ir.attachment"].create({
                    "datas": TEXT,
                    "name": f"fileText_test{i}.txt",
                    "mimetype": "text/plain",
                    "res_model": "account.move",
                    "res_id": invoice_test.id,
                })
                attachment.register_as_main_attachment(force=False)
                attachments |= attachment

            document = self.env["documents.document"].search(
                [("attachment_id", "=", attachments[0].id)]
            )
            self.assertEqual(
                document.folder_id, folder_test, "the text test document have a folder"
            )

            def check_main_attachment_and_document(
                main_attachment, doc_attachment, previous_attachment_ids
            ):
                self.assertRecordValues(
                    invoice_test,
                    [{"message_main_attachment_id": main_attachment.id}],
                )
                self.assertRecordValues(
                    document,
                    [
                        {
                            "attachment_id": doc_attachment.id,
                            "previous_attachment_ids": previous_attachment_ids,
                        }
                    ],
                )

            # Ensure the main attachment is the first one and ensure the document is correctly linked
            check_main_attachment_and_document(attachments[0], attachments[0], [])

            # Switch the main attachment to the second one and ensure the document is updated correctly
            invoice_test.write({"message_main_attachment_id": attachments[1].id})
            check_main_attachment_and_document(
                attachments[1], attachments[1], attachments[0].ids
            )

            # Switch the main attachment to the third one and ensure the document is updated correctly
            attachments[2].register_as_main_attachment(force=True)
            check_main_attachment_and_document(
                attachments[2], attachments[2], (attachments[0] + attachments[1]).ids
            )

            # Ensure all attachments are still linked to the invoice
            attachments = self.env["ir.attachment"].search(
                [("res_model", "=", "account.move"), ("res_id", "=", invoice_test.id)]
            )
            self.assertEqual(
                len(attachments),
                3,
                "there should be 3 attachments linked to the invoice",
            )

            # deleting the setting to prevent duplicate settings.
            setting.unlink()

    def test_bridge_account_account_settings_on_write_with_versioning(self):
        """
        With accounting-document centralization activated, make sure that the right attachment
        is set as main attachment on the invoice when versioning is involved and only one document
        is being created and updated.
        """
        folder_test = self.env["documents.document"].create({"name": "folder_test", "type": "folder"})
        self.env.user.company_id.documents_account_settings = True

        invoice_test = (
            self.env["account.move"]
            .with_context(default_move_type="in_invoice")
            .create({
                "name": "invoice_test",
                "move_type": "in_invoice",
            })
        )

        self.env["documents.account.folder.setting"].create({
            "folder_id": folder_test.id,
            "journal_id": invoice_test.journal_id.id,
        })

        attachments = self.env["ir.attachment"]
        for i in range(1, 3):
            attachment = self.env["ir.attachment"].create({
                "datas": TEXT,
                "name": f"attachment-{i}.txt",
                "mimetype": "text/plain",
                "res_model": "account.move",
                "res_id": invoice_test.id,
            })
            attachment.register_as_main_attachment(force=False)
            attachments |= attachment

        first_attachment, second_attachment = attachments[0], attachments[1]

        document = self.env["documents.document"].search(
            [("res_model", "=", "account.move"), ("res_id", "=", invoice_test.id)]
        )
        self.assertEqual(
            len(document), 1, "there should be 1 document linked to the invoice"
        )
        self.assertEqual(
            document.folder_id, folder_test, "the text test document have a folder"
        )

        def check_main_attachment_and_document(
            main_attachment, doc_attachment, previous_attachment_ids
        ):
            self.assertRecordValues(
                invoice_test,
                [{"message_main_attachment_id": main_attachment.id}],
            )
            self.assertRecordValues(
                document,
                [
                    {
                        "attachment_id": doc_attachment.id,
                        "previous_attachment_ids": previous_attachment_ids,
                    }
                ],
            )

        # Ensure the main attachment is attachment-1
        check_main_attachment_and_document(first_attachment, first_attachment, [])

        # Version the main attachment:
        # attachment-1 become attachment-3
        # version attachement become attachment-1
        document.write({
            "datas": TEXT,
            "name": "attachment-3.txt",
            "mimetype": "text/plain",
        })
        third_attachment = document.attachment_id
        first_attachment = document.previous_attachment_ids[0]
        check_main_attachment_and_document(
            third_attachment, third_attachment, first_attachment.ids
        )

        # Switch main attachment to attachment-2
        second_attachment.register_as_main_attachment(force=True)
        check_main_attachment_and_document(
            second_attachment,
            second_attachment,
            (first_attachment + third_attachment).ids,
        )

        # restore versioned attachment (attachment-1)
        document.write({"attachment_id": document.previous_attachment_ids[0].id})
        check_main_attachment_and_document(
            second_attachment,
            first_attachment,
            (third_attachment + second_attachment).ids,
        )

        # Switch main attachment to attachment-3
        third_attachment.register_as_main_attachment(force=True)
        check_main_attachment_and_document(
            third_attachment,
            third_attachment,
            (second_attachment + first_attachment).ids,
        )

        # Ensure there is still only one document linked to the invoice
        document = self.env["documents.document"].search(
            [("res_model", "=", "account.move"), ("res_id", "=", invoice_test.id)]
        )
        self.assertEqual(
            len(document), 1, "there should be 1 document linked to the invoice"
        )

    def test_journal_entry(self):
        """
        Makes sure the settings apply their values when an ir_attachment is set as message_main_attachment_id
        on invoices.
        """
        folder_test = self.env['documents.document'].create({'name': 'Bills', 'type': 'folder'})
        self.env.user.company_id.documents_account_settings = True

        invoice_test = self.env['account.move'].with_context(default_move_type='entry').create({
            'name': 'Journal Entry',
            'move_type': 'entry',
        })
        setting = self.env['documents.account.folder.setting'].create({
            'folder_id': folder_test.id,
            'journal_id': invoice_test.journal_id.id,
        })
        attachments = self.env['ir.attachment'].create([{
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'account.move',
            'res_id': invoice_test.id
        }, {
            'datas': TEXT,
            'name': 'fileText_test2.txt',
            'mimetype': 'text/plain',
            'res_model': 'account.move',
            'res_id': invoice_test.id
        }])
        documents = self.env['documents.document'].search([('attachment_id', 'in', attachments.ids)])
        self.assertEqual(len(documents), 2)
        setting.unlink()

    def test_bridge_account_sync_partner(self):
        """
        Tests that the partner is always synced on the document, regardless of settings
        """
        partner_1, partner_2 = self.env['res.partner'].create([{'name': 'partner_1'}, {'name': 'partner_2'}])
        self.document_txt.partner_id = partner_1
        (self.document_txt | self.document_gif).account_create_account_move('in_invoice')
        move = self.env['account.move'].browse(self.document_txt.res_id)
        self.assertEqual(move.partner_id, partner_1)
        move.partner_id = partner_2
        self.assertEqual(self.document_txt.partner_id, partner_2)

    def test_embedded_pdf(self):
        document = self.env['documents.document'].create({
            'name': 'test',
            'folder_id': self.folder_a.id,
            'datas': base64.b64encode(b'<?xml version="1.0" ?>\n<test> </test>'),
        })
        self.assertEqual(document.mimetype, 'text/xml' if magic else 'application/xml')
        self.assertFalse(document._extract_pdf_from_xml())
        self.assertFalse(document.thumbnail_status)
        self.assertFalse(document.has_embedded_pdf)

        document = self.env['documents.document'].create({
            'name': 'test',
            'folder_id': self.folder_a.id,
            'datas': base64.b64encode(b'<?xml version="1.0" ?>\n<test> <Attachment>JVBERi0gRmFrZSBQREYgY29udGVudA==</Attachment> </test>'),
        })
        self.assertEqual(document.mimetype, 'text/xml' if magic else 'application/xml')
        self.assertEqual(document._extract_pdf_from_xml(), b'%PDF- Fake PDF content')
        self.assertEqual(document.thumbnail_status, 'client_generated')
        self.assertTrue(document.has_embedded_pdf)

    def test_move_document_unlink(self):
        """Test that the document is sent to trash when the `account.move` is unlinked."""
        document1, document2 = self.document_txt, self.document_gif
        (document1 | document2).account_create_account_move('in_invoice')
        self.assertEqual(document1.res_model, "account.move")
        self.assertEqual(document2.res_model, "account.move")
        move1 = self.env["account.move"].browse(document1.res_id).exists()
        move2 = self.env["account.move"].browse(document2.res_id).exists()
        self.assertTrue(move1)
        self.assertTrue(move2)
        attachment1 = self.env['ir.attachment'].search([
            ('res_model', '=', move1._name),
            ('res_id', '=', move1.id),
        ])
        attachment2 = self.env['ir.attachment'].search([
            ('res_model', '=', move2._name),
            ('res_id', '=', move2.id),
        ])
        # attachment not linked to a document
        attachment3 = self.env['ir.attachment'].create({
            'name': 'Attachment 3',
            'res_model': move2._name,
            'res_id': move2.id,
        })
        self.assertEqual(len(attachment1), 1)
        self.assertEqual(len(attachment2), 1)

        self.env.flush_all()
        with self.assertQueryCount(73):
            (move1 | move2).unlink()

        self.assertTrue(attachment1.exists())
        self.assertTrue(document1.exists())
        self.assertFalse(document1.active)

        self.assertTrue(attachment2.exists())
        self.assertTrue(document2.exists())
        self.assertFalse(document2.active)

        self.assertFalse(attachment3.exists(),
            "That attachment is not linked to a record and so it should be removed")

        # removing the document in the trash clean the attachment
        document2.unlink()
        self.assertFalse(attachment2.exists())

    def test_workflow_create_misc_entry(self):
        misc_entry_action = (self.document_txt | self.document_gif).account_create_account_move('entry')
        move = self.env['account.move'].browse(self.document_txt.res_id)
        self.assertEqual(misc_entry_action.get('res_model'), 'account.move')
        self.assertEqual(move.move_type, 'entry')

    def test_workflow_create_bank_statement_raise(self):
        with self.assertRaises(UserError): # Could not make sense of the given file.
            (self.document_txt | self.document_gif).account_create_account_bank_statement()

        self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', 'bank'),
            ]).unlink()

        for sudo in False, True:
            # Running test with sudo similulates server actions that run with sudo rights
            with self.subTest(sudo=sudo), self.assertRaises(UserError) as err:
                self.document_txt.sudo(sudo).account_create_account_bank_statement()
            self.assertEqual(
                err.exception.args[0],
                "No journal could be found in company company_1_data for any of those types: bank",
            )

    def test_workflow_create_vendor_bill(self):
        vendor_bill_entry_action = self.document_txt.account_create_account_move('in_invoice')
        move = self.env['account.move'].browse(self.document_txt.res_id)
        self.assertEqual(vendor_bill_entry_action.get('res_model'), 'account.move')
        self.assertEqual(move.move_type, 'in_invoice')

    def test_workflow_create_vendor_receipt(self):
        # Activate the group for the vendor receipt
        self.env['res.config.settings'].create({'group_show_purchase_receipts': True}).execute()
        self.assertTrue(self.env.user.has_group('account.group_purchase_receipts'), 'The "purchase Receipt" feature should be enabled.')

        vendor_receipt_action = self.document_txt.account_create_account_move('in_receipt')
        move = self.env['account.move'].browse(self.document_txt.res_id)
        self.assertEqual(vendor_receipt_action.get('res_model'), 'account.move')
        self.assertEqual(move.move_type, 'in_receipt')

    def test_documents_xml_attachment(self):
        """
        Makes sure pdf and xml created by the system will create a document
        """
        self.env.user.company_id.documents_account_settings = True
        folder_test = self.env['documents.document'].create({'name': 'Bills', 'type': 'folder'})

        invoice = self.init_invoice("out_invoice", amounts=[1000], post=True)
        setting = self.env['documents.account.folder.setting'].create({
            'folder_id': folder_test.id,
            'journal_id': invoice.journal_id.id,
        })
        att_ids = []
        for fmt in ('xml', 'txt'):
            attachment = self.env["ir.attachment"].create({
                "raw": "<text/>",
                "name": f"attachment-{fmt}.txt",
                "mimetype": f"application/{fmt}",
                "res_model": "account.move",
                "res_id": invoice.id,
            })
            att_ids.append(attachment.id)
        documents = self.env['documents.document'].search([('attachment_id', 'in', att_ids)])
        self.assertEqual(len(documents), 1, "TXT should not create a document")
        attachment_pdf = self.env['ir.attachment'].create({
            'datas': PDF,
            'name': 'file.pdf',
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
        })
        documents = self.env['documents.document'].search([('attachment_id', '=', attachment_pdf.id)])
        self.assertFalse(documents, "pdf should not be attached if not main attachment")
        attachment_pdf.register_as_main_attachment(force=False)
        documents = self.env['documents.document'].search([('attachment_id', '=', attachment_pdf.id)])
        self.assertEqual(len(documents), 1, "Pdf registered as main attachment did not create a single document")
        setting.unlink()

    def test_gc_clear_bin_for_journal_folder(self):
        """Check that account setting folders are excluded from garbage collector."""
        folder_setting, other_folder = self.env['documents.document'].create([
            {'name': 'Folder setting', 'type': 'folder'},
            {'name': 'Other folder', 'type': 'folder'},
        ])
        self.env['documents.account.folder.setting'].create({
            'folder_id': folder_setting.id,
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        (folder_setting | other_folder).action_archive()
        document_deletion_date = folder_setting.write_date + timedelta(
            days=folder_setting.get_deletion_delay(), seconds=30)
        with freeze_time(document_deletion_date):
            self.env["documents.document"]._gc_clear_bin()

        self.assertTrue(folder_setting.exists(),
                        "folder linked to journal setting should not be deleted after gc_clear_bin")
        self.assertFalse(other_folder.exists(),
                        "folder not linked to journal setting should be deleted after gc_clear_bin")


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMoveSendDocument(TestAccountMoveSendCommon):

    def test_send_and_print_document_creation(self):
        """
        Makes sure the documents are created when attaching pdf and xml to the move
        """
        self.env.user.company_id.documents_account_settings = True
        folder_test = self.env['documents.document'].create({'name': 'Bills', 'type': 'folder'})
        move = self.init_invoice("out_invoice", amounts=[1000], post=True)
        setting = self.env['documents.account.folder.setting'].create({
            'folder_id': folder_test.id,
            'journal_id': move.journal_id.id,
        })

        wizard = self.create_send_and_print(move)
        wizard.action_send_and_print()
        attachments = move.attachment_ids | move.invoice_pdf_report_id
        documents = self.env['documents.document'].search([('attachment_id', 'in', attachments.ids)])
        self.assertEqual(len(documents), len(attachments), "Each move attachment should create a corresponding document")
        with patch.object(Document, '_get_is_multipage', return_value=False):
            setting.unlink()
