# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import http
from odoo.tests.common import HttpCase, new_test_user

from .common import SpreadsheetTestCommon
from odoo.tools import file_open
from odoo.exceptions import UserError


class SpreadsheetImportXlsx(HttpCase, SpreadsheetTestCommon):
    def test_import_xlsx(self):
        """Import xlsx"""
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})
        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            spreadsheet_data = base64.encodebytes(f.read())
            document_xlsx = self.env['documents.document'].create({
                'datas': spreadsheet_data,
                'name': 'text.xlsx',
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'folder_id': folder.id
            })
            spreadsheet_id = document_xlsx.clone_xlsx_into_spreadsheet()
            spreadsheet = self.env["documents.document"].browse(spreadsheet_id).exists()
            self.assertTrue(spreadsheet)

    def test_import_xlsx_WPS_mimetype(self):
        """Import xlsx"""
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})
        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            raw = f.read()
            document_xlsx = self.env['documents.document'].create({
                'raw': raw,
                'name': 'text.xlsx',
                'mimetype': 'application/wps-office.xlsx',
                'folder_id': folder.id
            })
            spreadsheet_id = document_xlsx.clone_xlsx_into_spreadsheet()
            spreadsheet = self.env["documents.document"].browse(spreadsheet_id).exists()
            self.assertTrue(spreadsheet)

    def test_import_xlsx_wrong_mime_type(self):
        """Import xlsx with wrong mime type raisese an error"""
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})
        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            spreadsheet_data = base64.encodebytes(f.read())
            document_xlsx = self.env['documents.document'].create({
                'datas': spreadsheet_data,
                'name': 'text.xlsx',
                'mimetype': 'text/plain',
                'folder_id': folder.id
            })
            with self.assertRaises(UserError) as error_catcher:
                document_xlsx.clone_xlsx_into_spreadsheet()

            self.assertEqual(error_catcher.exception.args[0], ("The file is not a xlsx file"))


    def test_import_xlsx_wrong_content(self):
        """Import a xlsx which isn't a zip raises error"""
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})
        document_xlsx = self.env['documents.document'].create({
            'datas': base64.encodebytes(b"yolo"),
            'name': 'text.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'folder_id': folder.id
        })
        with self.assertRaises(UserError) as error_catcher:
            document_xlsx.clone_xlsx_into_spreadsheet()

        self.assertEqual(error_catcher.exception.args[0], ("The file is not a xlsx file"))

    def test_import_xlsx_zip_but_not_xlsx(self):
        """Import a zip which isn't a xlsx raises error"""
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})
        document_xlsx = self.env['documents.document'].create({
            # Minimum zip file
            'datas': base64.encodebytes(b"\x50\x4B\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"),
            'name': 'text.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'folder_id': folder.id
        })
        with self.assertRaises(UserError) as error_catcher:
            document_xlsx.clone_xlsx_into_spreadsheet()

        self.assertEqual(error_catcher.exception.args[0], ("The xlsx file is corrupted"))

    def test_import_xlsx_computes_multipage(self):
        """Import xlsx leads to accurate multipage computation"""
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})

        cases = [('test.xlsx', False), ('test2sheets.xlsx', True)]

        for filename, is_multipage in cases:
            with file_open(f'documents_spreadsheet/tests/data/{filename}', 'rb') as f:
                spreadsheet_data = base64.encodebytes(f.read())
                document_xlsx = self.env['documents.document'].create(
                    {
                        'datas': spreadsheet_data,
                        'name': filename,
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'folder_id': folder.id,
                    }
                )
                with self.subTest(is_multipage=is_multipage, kind="xlsx"):
                    self.assertEqual(document_xlsx.is_multipage, is_multipage)

            spreadsheet_id = document_xlsx.clone_xlsx_into_spreadsheet()
            spreadsheet = self.env["documents.document"].browse(spreadsheet_id).exists()
            with self.subTest(is_multipage=is_multipage, kind="spreadsheet"):
                self.assertEqual(spreadsheet.is_multipage, is_multipage)

    def test_compute_xlsx_multipage_does_not_create_attachment(self):
        """multipage computation does not create the xlsx attachments in the database"""
        filename = "test_with_image.xlsx"

        with file_open(f'documents_spreadsheet/tests/data/{filename}', 'rb') as f:
            spreadsheet_data = base64.encodebytes(f.read())
            new_document = self.env['documents.document'].create(
                {
                    'datas': spreadsheet_data,
                    'name': filename,
                    'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                }
            )
        attachment_count = self.env['ir.attachment'].search_count([('res_model', '=', 'documents.document')])
        new_document.is_multipage
        new_attachment_count = self.env['ir.attachment'].search_count([('res_model', '=', 'documents.document')])
        self.assertEqual(attachment_count, new_attachment_count)

    def test_request_xlsx_computes_multipage(self):
        """Successfully upload xlsx on requested documents"""
        self.authenticate('spreadsheetDude', 'spreadsheetDude')
        folder = self.env["documents.document"].create({"name": "Test folder", "type": "folder"})
        activity_type = self.env['mail.activity.type'].create({
            'name': 'request_document',
            'category': 'upload_file',
            'folder_id': folder.id,
        })
        document = self.env['documents.request_wizard'].create({
            'name': 'Wizard Request',
            'requestee_id': self.spreadsheet_user.partner_id.id,
            'activity_type_id': activity_type.id,
            'folder_id': folder.id,
        }).request_document()

        with file_open('documents_spreadsheet/tests/data/test2sheets.xlsx', 'rb') as file:
            response = self.url_open(
                url='/documents/upload',
                data={
                    'access_token': document.access_token,
                    'csrf_token': http.Request.csrf_token(self),
                },
                files=[('ufile', ('test2sheets.xlsx', file.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [document.id])
        self.assertEqual(document.is_multipage, True)

    def test_spreadsheet_conversion_with_portal_user(self):
        """Test XLSX to Spreadsheet conversion with portal user who is `edit` role of the folder."""
        portal_user = new_test_user(self.env, login='test_portal', groups='base.group_portal')
        portal_user_doc_owner = new_test_user(self.env, login='test_portal_doc_owner', groups='base.group_portal')

        partners = {
            portal_user.partner_id: ('edit', False),
            portal_user_doc_owner.partner_id: ('edit', False),
        }

        folder = self.env['documents.document'].create({'name': 'Test folder', 'type': 'folder'})
        folder.action_update_access_rights(partners=partners)

        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            spreadsheet_data = base64.encodebytes(f.read())

        document_xlsx = self.env['documents.document'].create({
            'datas': spreadsheet_data,
            'name': 'text.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'folder_id': folder.id,
            'owner_id': portal_user_doc_owner.id
        })
        spreadsheet_id = document_xlsx.clone_xlsx_into_spreadsheet()
        spreadsheet = self.env['documents.document'].browse(spreadsheet_id).exists()

        self.assertTrue(spreadsheet)
        # Spreadsheets can not be shared in edit mode to non-internal users.
        # `clone_xlsx_into_spreadsheet()` should have adjusted portal users' role during the conversion.
        portal_user_roles = spreadsheet.access_ids.filtered(lambda x: x.partner_id.user_ids.share).mapped('role')
        self.assertListEqual(portal_user_roles, ['view', 'view'])
