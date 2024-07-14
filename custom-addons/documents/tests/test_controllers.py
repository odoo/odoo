# -*- coding: utf-8 -*-

import io
import zipfile
import base64

from odoo import http, fields
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tools import mute_logger


class TestDocumentsRoutes(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.folder_a, self.folder_b = self.env['documents.folder'].create([
            {'name': 'folder A'},
            {'name': 'folder B'},
        ])
        self.document_txt = self.env['documents.document'].create({
            'raw': b'TEST',
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
        })
        self.share_folder_b = self.env['documents.share'].create(
            {
                'folder_id': self.folder_b.id,
                'type': 'domain',
                'action': 'downloadupload',
            }
        )

    def test_documents_content(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/documents/content/%s' % self.document_txt.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'TEST')

    def test_documents_zip(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/document/zip', data={
            'file_ids': [self.document_txt.id],
            'zip_name': 'testZip.zip',
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertEqual(response.status_code, 200)
        with io.BytesIO(response.content) as buffer, zipfile.ZipFile(buffer) as zipfile_obj:
            self.assertEqual(zipfile_obj.read(self.document_txt.name), b'TEST')

    def test_documents_zip_authentification(self):

        self.authenticate('admin', 'admin')

        vals = {
            "name": "private_folder",
            "parent_folder_id": False,
            "company_id": False,
            "facet_ids": [],
            "group_ids": [self.env.ref('base.group_system').id],
            "user_specific_write": True,
            "read_group_ids": [self.env.ref('base.group_system').id],
            "user_specific": True,
            "description": False
        }
        workspace_private = self.env['documents.folder'].create(vals)

        vals = {
            "name": "public_folder",
        }
        workspace_public = self.env['documents.folder'].create(vals)

        rawpdf_base64 = 'JVBERi0xLjYNJeLjz9MNCjI0IDAgb2JqDTw8L0ZpbHRlci9GbGF0ZURlY29kZS9GaXJzdCA0L0xlbmd0aCAyMTYvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjePI9RS8MwFIX/yn1bi9jepCQ6GYNpFBTEMsW97CVLbjWYNpImmz/fVsXXcw/f/c4SEFarepPTe4iFok8dU09DgtDBQx6TMwT74vaLTE7uSPDUdXM0Xe/73r1FnVwYYEtHR6d9WdY3kX4ipRMV6oojSmxQMoGyac5RLBAXf63p38aGA7XPorLewyvFcYaJile8rB+D/YcwiRdMMGScszO8/IW0MdhsaKKYGA46gXKTr/cUQVY4We/cYMNpnLVeXPJUXHs9fECr7kAFk+eZ5Xr9LcAAfKpQrA0KZW5kc3RyZWFtDWVuZG9iag0yNSAwIG9iag08PC9GaWx0ZXIvRmxhdGVEZWNvZGUvRmlyc3QgNC9MZW5ndGggNDkvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjeslAwULCx0XfOL80rUTDU985MKY42NAIKBsXqh1QWpOoHJKanFtvZAQQYAN/6C60NCmVuZHN0cmVhbQ1lbmRvYmoNMjYgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDkvTGVuZ3RoIDQyL04gMi9UeXBlL09ialN0bT4+c3RyZWFtDQpo3jJTMFAwVzC0ULCx0fcrzS2OBnENFIJi7eyAIsH6LnZ2AAEGAI2FCDcNCmVuZHN0cmVhbQ1lbmRvYmoNMjcgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDUvTGVuZ3RoIDEyMC9OIDEvVHlwZS9PYmpTdG0+PnN0cmVhbQ0KaN4yNFIwULCx0XfOzytJzSspVjAyBgoE6TsX5Rc45VdEGwB5ZoZGCuaWRrH6vqkpmYkYogGJRUCdChZgfUGpxfmlRcmpxUAzA4ryk4NTS6L1A1zc9ENSK0pi7ez0g/JLEktSFQz0QyoLUoF601Pt7AACDADYoCeWDQplbmRzdHJlYW0NZW5kb2JqDTIgMCBvYmoNPDwvTGVuZ3RoIDM1MjUvU3VidHlwZS9YTUwvVHlwZS9NZXRhZGF0YT4+c3RyZWFtDQo8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjQtYzAwNSA3OC4xNDczMjYsIDIwMTIvMDgvMjMtMTM6MDM6MDMgICAgICAgICI+CiAgIDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnBkZj0iaHR0cDovL25zLmFkb2JlLmNvbS9wZGYvMS4zLyIKICAgICAgICAgICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICAgICAgICAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgICAgICAgICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIj4KICAgICAgICAgPHBkZjpQcm9kdWNlcj5BY3JvYmF0IERpc3RpbGxlciA2LjAgKFdpbmRvd3MpPC9wZGY6UHJvZHVjZXI+CiAgICAgICAgIDx4bXA6Q3JlYXRlRGF0ZT4yMDA2LTAzLTA2VDE1OjA2OjMzLTA1OjAwPC94bXA6Q3JlYXRlRGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdG9yVG9vbD5BZG9iZVBTNS5kbGwgVmVyc2lvbiA1LjIuMjwveG1wOkNyZWF0b3JUb29sPgogICAgICAgICA8eG1wOk1vZGlmeURhdGU+MjAxNi0wNy0xNVQxMDoxMjoyMSswODowMDwveG1wOk1vZGlmeURhdGU+CiAgICAgICAgIDx4bXA6TWV0YWRhdGFEYXRlPjIwMTYtMDctMTVUMTA6MTI6MjErMDg6MDA8L3htcDpNZXRhZGF0YURhdGU+CiAgICAgICAgIDx4bXBNTTpEb2N1bWVudElEPnV1aWQ6ZmYzZGNmZDEtMjNmYS00NzZmLTgzOWEtM2U1Y2FlMmRhMmViPC94bXBNTTpEb2N1bWVudElEPgogICAgICAgICA8eG1wTU06SW5zdGFuY2VJRD51dWlkOjM1OTM1MGIzLWFmNDAtNGQ4YS05ZDZjLTAzMTg2YjRmZmIzNjwveG1wTU06SW5zdGFuY2VJRD4KICAgICAgICAgPGRjOmZvcm1hdD5hcHBsaWNhdGlvbi9wZGY8L2RjOmZvcm1hdD4KICAgICAgICAgPGRjOnRpdGxlPgogICAgICAgICAgICA8cmRmOkFsdD4KICAgICAgICAgICAgICAgPHJkZjpsaSB4bWw6bGFuZz0ieC1kZWZhdWx0Ij5CbGFuayBQREYgRG9jdW1lbnQ8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6QWx0PgogICAgICAgICA8L2RjOnRpdGxlPgogICAgICAgICA8ZGM6Y3JlYXRvcj4KICAgICAgICAgICAgPHJkZjpTZXE+CiAgICAgICAgICAgICAgIDxyZGY6bGk+RGVwYXJ0bWVudCBvZiBKdXN0aWNlIChFeGVjdXRpdmUgT2ZmaWNlIG9mIEltbWlncmF0aW9uIFJldmlldyk8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6U2VxPgogICAgICAgICA8L2RjOmNyZWF0b3I+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgog' + 682*'ICAg' + 'Cjw/eHBhY2tldCBlbmQ9InciPz4NCmVuZHN0cmVhbQ1lbmRvYmoNMTEgMCBvYmoNPDwvTWV0YWRhdGEgMiAwIFIvUGFnZUxhYmVscyA2IDAgUi9QYWdlcyA4IDAgUi9UeXBlL0NhdGFsb2c+Pg1lbmRvYmoNMjMgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0xlbmd0aCAxMD4+c3RyZWFtDQpIiQIIMAAAAAABDQplbmRzdHJlYW0NZW5kb2JqDTI4IDAgb2JqDTw8L0RlY29kZVBhcm1zPDwvQ29sdW1ucyA0L1ByZWRpY3RvciAxMj4+L0ZpbHRlci9GbGF0ZURlY29kZS9JRFs8REI3Nzc1Q0NFMjI3RjZCMzBDNDQwREY0MjIxREMzOTA+PEJGQ0NDRjNGNTdGNjEzNEFCRDNDMDRBOUU0Q0ExMDZFPl0vSW5mbyA5IDAgUi9MZW5ndGggODAvUm9vdCAxMSAwIFIvU2l6ZSAyOS9UeXBlL1hSZWYvV1sxIDIgMV0+PnN0cmVhbQ0KaN5iYgACJjDByGzIwPT/73koF0wwMUiBWYxA4v9/EMHA9I/hBVCxoDOQeH8DxH2KrIMIglFwIpD1vh5IMJqBxPpArHYgwd/KABBgAP8bEC0NCmVuZHN0cmVhbQ1lbmRvYmoNc3RhcnR4cmVmDQo0NTc2DQolJUVPRg0K'
        rawpdf = base64.b64decode(rawpdf_base64.encode())

        private_doc = self.env['documents.document'].create({
            'raw': rawpdf,
            'name': 'private_file.pdf',
            'mimetype': 'application/pdf',
            'folder_id': workspace_private.id,
        })

        document_group_id_manager = self.env.ref('documents.group_documents_manager')
        document_group_id_user = self.env.ref('documents.group_documents_user')

        user = self.env.user.create({'name': 'test_doc', 'login': 'test_doc', 'password': 'test_doc'})   # User with explicitely removed manager right and given user right on the document app
        user.groups_id -= document_group_id_manager
        user.groups_id += document_group_id_user

        self.assertNotIn(private_doc, self.env['documents.document'].with_user(user.id).search([]))   # Our new user should not be able to find the private doc

        document_public = self.env['documents.document'].create({
            'raw': rawpdf,
            'name': 'public.pdf',
            'mimetype': 'application/pdf',
            'folder_id': workspace_public.id,
        })

        self.assertIn(document_public, self.env['documents.document'].with_user(user.id).search([])) # but he should see the public document

        self.authenticate('test_doc', 'test_doc')

        with mute_logger('odoo.http'):
            response = self.url_open('/document/zip', data={
                'file_ids': f'{private_doc.id},{document_public.id}',
                'zip_name': 'testZip.zip',
                'csrf_token': http.Request.csrf_token(self),
            })
            self.assertNotEqual(response.status_code, 200)

        with mute_logger('odoo.http'):
            response = self.url_open('/document/zip', data={
                'file_ids': f'{document_public.id},{private_doc.id}',
                'zip_name': 'testZip.zip',
                'csrf_token': http.Request.csrf_token(self),
            })
            self.assertNotEqual(response.status_code, 200)

    def test_documents_from_web(self):
        self.authenticate('admin', 'admin')
        raw_gif = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
        document_gif = self.env['documents.document'].create({
            'raw': raw_gif,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_a.id,
        })
        response = self.url_open('/web/image/%s?model=documents.document' % document_gif.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, raw_gif)

    def test_documents_share_expired_link(self):
        self.authenticate('admin', 'admin')
        # Test on available link
        tomorrow = fields.Date.from_string(fields.Date.add(fields.Date.today(), days=1))
        vals = {
            'document_ids': [(6, 0, [self.document_txt.id])],
            'folder_id': self.folder_a.id,
            'date_deadline': tomorrow,
            'type': 'ids',
        }
        self.result_share_documents_act = self.env['documents.share'].create(vals)
        response = self.url_open(self.result_share_documents_act.full_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'is sharing content with you', response.content, "Failed route test on available link")

        # Test on expired link
        vals = {
            'document_ids': [(6, 0, [self.document_txt.id])],
            'folder_id': self.folder_a.id,
            'date_deadline': '2001-11-05',
            'type': 'ids',
        }
        self.result_share_documents_act = self.env['documents.share'].create(vals)
        response = self.url_open(self.result_share_documents_act.full_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Sorry, this link is no longer valid.' in response.content, "Failed route test on expired link")

    def test_download_all_documents_with_url(self):
        document_url = self.env['documents.document'].create({
            'name': 'file.txt',
            'type': 'url',
            'folder_id': self.folder_a.id,
        })
        vals = {
            'document_ids': [(6, 0, [self.document_txt.id, document_url.id])],
            'folder_id': self.folder_a.id,
            'type': 'ids',
        }
        share = self.env['documents.share'].create(vals)
        response = self.url_open(f"/document/download/all/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)

    def test_upload_attachment_public(self):
        """Check the upload and notifications for public users."""
        files = [('files', ('test.txt', b'test', 'image/svg+xml'))]
        response = self.url_open(
            f'/document/upload/{self.share_folder_b.id}/{self.share_folder_b.access_token}', files=files
        )
        document = self.env['documents.document'].search([('folder_id', '=', self.folder_b.id)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(document), 1)
        self.assertEqual(document.name, 'test.txt')
        self.assertEqual(document.raw, b'test')
        self.assertEqual(document.mimetype, 'text/plain')

        public_user = self.env.ref('base.public_user')
        file_uploaded_note = document.message_ids[0]
        self.assertEqual(file_uploaded_note.author_id, public_user.partner_id)
        self.assertIn('<b>File uploaded by:</b> Public user <br>', file_uploaded_note.body)
        self.assertIn(f'<b>Link created by:</b> {self.share_folder_b.create_uid.name}', file_uploaded_note.body)

    def test_upload_attachment_user(self):
        """Check that logged user's name is used in notification."""
        files = [('files', ('test.txt', b'test', 'text/plain'))]
        demo_session = self.authenticate('demo', 'demo')
        demo_user = self.env['res.users'].browse(demo_session.uid)
        self.url_open(f'/document/upload/{self.share_folder_b.id}/{self.share_folder_b.access_token}', files=files)
        document = self.env['documents.document'].search([('folder_id', '=', self.folder_b.id)])

        file_uploaded_note = document.message_ids[0]
        self.assertEqual(file_uploaded_note.author_id, demo_user.partner_id)
        self.assertIn('<b>File uploaded by:</b> Marc Demo <br>', file_uploaded_note.body)
        self.assertIn(f'<b>Link created by:</b> {self.share_folder_b.create_uid.name}', file_uploaded_note.body)
