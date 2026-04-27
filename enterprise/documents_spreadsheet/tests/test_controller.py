import json

from odoo import http

from odoo.tests.common import HttpCase
from odoo.tools.misc import mute_logger

from .common import SpreadsheetTestCommon


class TestSpreadsheetDocumentController(SpreadsheetTestCommon, HttpCase):

    def test_upload_osheet_json_file(self):
        self.authenticate('admin', 'admin')
        folder = self.env['documents.document'].create({'name': 'Test folder', 'type': 'folder', 'access_internal': 'edit'})

        data = {'sheets': []}

        for name in ['test.osheet.json', 'test.osheet (5).json', 'test.osheet(5).json']:
            with self.subTest(name=name):
                response = self.url_open(
                    url='/documents/upload',
                    data={
                        'access_token': folder.access_token,
                        'csrf_token': http.Request.csrf_token(self),
                    },
                    files=[('ufile', (name, json.dumps(data), 'application/json'))],
                )

                self.assertEqual(response.status_code, 200)
                document = self.env['documents.document'].browse(response.json())
                self.assertEqual(document.handler, 'spreadsheet')
                self.assertEqual(document.spreadsheet_data, json.dumps(data))

    def test_upload_osheet_not_json_file(self):
        self.authenticate('admin', 'admin')
        folder = self.env['documents.document'].create({'name': 'Test folder', 'type': 'folder', 'access_internal': 'edit'})
        data = 'not a json file'
        response = self.url_open(
            url='/documents/upload',
            data={
                'access_token': folder.access_token,
                'csrf_token': http.Request.csrf_token(self),
            },
            files=[('ufile', ('test.osheet.json', data, 'text/plain'))],
        )

        self.assertEqual(response.status_code, 200)
        document = self.env['documents.document'].browse(response.json())
        self.assertFalse(document.handler)
        self.assertFalse(document.spreadsheet_data)
        self.assertEqual(document.folder_id, folder)

    @mute_logger('odoo.http')
    def test_upload_invalid_osheet_json_file(self):
        self.authenticate('admin', 'admin')
        folder = self.env['documents.document'].create({'name': 'Test folder', 'type': 'folder', 'access_internal': 'edit'})
        data = {
            'sheets': [],
            'lists': {
                '1': {
                    'model': 'my.invalid.model',
                    'columns': [],
                    'domain': [],
                    'context': {},
                    'orderBy': [],
                    'id': '1',
                    'name': 'Purchase Orders by Untaxed Amount'
                }
            }
        }
        response = self.url_open(
            url='/documents/upload',
            data={
                'access_token': folder.access_token,
                'csrf_token': http.Request.csrf_token(self),
            },
            files=[('ufile', ('test.osheet.json', json.dumps(data), 'application/json'))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue('Looks like the spreadsheet file contains invalid data.' in response.text)
