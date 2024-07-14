import json
import base64

from io import BytesIO
from urllib.parse import urlparse
from zipfile import ZipFile

from odoo.tests.common import HttpCase, new_test_user
from odoo.tools import mute_logger

from .common import SpreadsheetTestCommon


class TestShareController(SpreadsheetTestCommon, HttpCase):
    def test_documents_share_portal(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        response = self.url_open(f"/document/share/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)

    def test_documents_share_portal_wrong_token(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        with mute_logger('odoo.http'):
            response = self.url_open(f"/document/share/{share.id}/a-random-token")
        # should probably be 403
        self.assertEqual(response.status_code, 404)

    def test_documents_share_portal_internal_redirect(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        new_test_user(self.env, login="raoul", password="Password!1")
        self.authenticate("raoul", "Password!1")
        response = self.url_open(f"/document/share/{share.id}/{share.access_token}")
        url = urlparse(response.url)
        self.assertEqual(url.path, "/web")
        self.assertEqual(
            url.fragment,
            f"spreadsheet_id={spreadsheet.id}&action=action_open_spreadsheet&access_token={share.access_token}&share_id={share.id}",
        )

    def test_public_spreadsheet(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        response = self.url_open(f"/document/spreadsheet/share/{share.id}/{share.access_token}/{spreadsheet.id}")
        self.assertEqual(response.status_code, 200)

    def test_public_spreadsheet_wrong_token(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/document/spreadsheet/share/{share.id}/a-random-token/{spreadsheet.id}")
        self.assertEqual(response.status_code, 403)

    def test_public_spreadsheet_other_document(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        other_spreadsheet = self.create_spreadsheet()
        response = self.url_open(f"/document/spreadsheet/share/{share.id}/{share.access_token}/{other_spreadsheet.id}")
        self.assertEqual(response.status_code, 404)

    def test_public_spreadsheet_data(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        shared_spreadsheet = share.freezed_spreadsheet_ids
        response = self.url_open(f"/document/spreadsheet/data/{shared_spreadsheet.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), json.loads(spreadsheet.spreadsheet_data))

    def test_public_spreadsheet_data_wrong_token(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        shared_spreadsheet = share.freezed_spreadsheet_ids
        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/document/spreadsheet/data/{shared_spreadsheet.id}/a-random-token")
        self.assertEqual(response.status_code, 403)

    def test_download_document(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        shared_spreadsheet = share.freezed_spreadsheet_ids
        shared_spreadsheet.excel_export = base64.b64encode(b"test")
        response = self.url_open(f"/document/download/{share.id}/{share.access_token}/{spreadsheet.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"test")

    def test_download_document_wrong_token(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        shared_spreadsheet = share.freezed_spreadsheet_ids
        shared_spreadsheet.excel_export = base64.b64encode(b"test")
        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/document/download/{share.id}/a-random-token/{spreadsheet.id}")
        self.assertEqual(response.status_code, 403)

    def test_download_document_other_document(self):
        spreadsheet = self.create_spreadsheet()
        other_spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        shared_spreadsheet = share.freezed_spreadsheet_ids
        shared_spreadsheet.excel_export = base64.b64encode(b"test")
        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/document/download/{share.id}/{share.access_token}/{other_spreadsheet.id}")
        self.assertEqual(response.status_code, 403)

    def test_download_all_document(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        share.freezed_spreadsheet_ids.excel_export = base64.b64encode(b"test")
        response = self.url_open(f"/document/download/all/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(response.content)) as zip_file:
            self.assertEqual(len(zip_file.filelist), 1)
            file_content = zip_file.open(zip_file.filelist[0]).read()
            self.assertEqual(file_content, b"test")

    def test_download_all_document_with_missing_excel_file(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        share.freezed_spreadsheet_ids.excel_export = False
        response = self.url_open(f"/document/download/all/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(response.content)) as zip_file:
            self.assertEqual(len(zip_file.filelist), 0)

    def test_share_portal_document_folder_deletion(self):
        spreadsheet = self.create_spreadsheet()
        share = self.share_spreadsheet(spreadsheet)
        url = share.full_url
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)

        folder = spreadsheet.folder_id
        spreadsheet.unlink()
        folder.unlink()
        with mute_logger('odoo.http'):
            response = self.url_open(url)
        self.assertEqual(response.status_code, 404)

    def test_share_portal_folder_with_one_document(self):
        document = self.create_spreadsheet()
        url = self.env["documents.share"].action_get_share_url({
            'folder_id': document.folder_id.id,
            'domain': [],
            'document_ids': [(6, 0, [document.id])],
            'type': 'domain',
            'date_deadline': '3052-01-01',
            'action': 'downloadupload',
        })

        response = self.url_open(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Untitled Spreadsheet", response.text)
        self.assertIn('o_docs_share_page', response.text)
