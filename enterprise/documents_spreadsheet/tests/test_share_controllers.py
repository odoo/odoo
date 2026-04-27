import json

from io import BytesIO
from zipfile import ZipFile

from freezegun import freeze_time

from odoo.tests.common import HttpCase, new_test_user
from odoo.tools import mute_logger

from .common import SpreadsheetTestCommon


class TestShareController(SpreadsheetTestCommon, HttpCase):
    EXCEL_EXPORT = b'UEsDBBQAAAAIAOQ6MVkdRuZppwAAABwBAAAPAAAAeGwvd29ya2Jvb2sueG1sjZA9DoMwDIX3niLKAWro0AEBUxfmniCAaSKSGNnpz/GbgpDarZ7e87O+J7l+Es890axewUdptE1pqQBksBiMHGnBmJOJOJiULd9AFkYzikVMwcOpKM4QjIt6I1T8D4OmyQ14oeEeMKYNwuhNchTFukV0e1Dr1GuR7Fapn72SZBI2+uHE9R61iiZke/1kpVbrTTc2OmuuXBbcjaWGjbaT4Luihv0j7RtQSwMEFAAAAAgA5DoxWfEBlyPOAQAASAoAABgAAAB4bC93b3Jrc2hlZXRzL3NoZWV0MC54bWytlsFO4zAQhu99CisPUGdc2gIKlRBoF6Q9rPYAZ2/iEos4rmyX8PjrpJ4QghYhND2l4+QbjTSf/Beddc++ViqwV9O0/iqrQzhccu7LWhnpl/ag2niyt87IEP+6J+4PTslq+Mg0XOT5hhup2+xEuHRfYdj9Xpfq1pZHo9pwgjjVyKBt62t98NluwdJv/lAMrR+06vzbS29F5mvb/XS6+qVbFQeCjPVD/rX2uT++r66yfEKf8As+QvB8UkrNZh1/DEP9dqxSe3lswh/b3Sn9VIfYeLsU6wwPbmzzqKtQx/pquV1lfDZgUdpmnAe7xxozuh2GMPL1NMyUwsqjD9YgOWO1rirV9iOmBosPLJFYgoC1SqwVAesssc4IWOvEWhOwNom1IWBtE2tLwDpPrHMC1kViXRCwIMdlzSlo4+pT7D7g8gPF9gOuP1DsP6AAQGEAoAJA4QCgBEBhAaAGQOEBoAhAYQKgCkDhgkAXBIULAl0QJPfAeBFQuCDQBUHhgkAXBIULAl0QFC4IdEF8w4UBxfGun0WAIVHcyiBnOSAeOdsx1zOnyaUo+9p1bBTjxikyFS+7vOAvu0VsMklHPH7/DpqCDTb7b9j65KHgY3jc/QNQSwMEFAAAAAgA5DoxWUmMTd5fAQAATgQAAA0AAAB4bC9zdHlsZXMueG1snVRNa8MwDL33V5j8gDkrbIfiFgajsPN22NVN5MTgL2x1tPv1c76dtBljvtjSk56eFTks4FXBew2A5KKVCfusRnQ7SkNRg+bhwTowERHWa47R9BUNzgMvQ5OkFd3m+TPVXJqsY9j5v3BYIWQBr7Y4azDYkXhQHKU1oZYuZIcNaVe7MXPWR42BFPZscJ/lC5j2eOOdAcKaKetxkdWAM8/KxsI3+eIqEuQZHRJYYZX1xFenKKddCWa4hi7lxUuuBoTRoWRi3hEtlRpFb3vRfUQPH0YzOhxHBG+O0U/688fVwT4z1sCkqi2Y5G7+Q1l5fn3cPv3COrlub3ayvgS/9kHGgIRbgcBUWVJ1DjEvq3otdIExtG4lcoZEOYhWr4QuQVZKXlnD1Ur8Em4YpttuUtdt5wpQ6lPc6Ry7CNJN/1vZPAzSdH44xvHqjx1vZ4zT2JPeFCsvYv2pNWAywtMf5PADUEsDBBQAAAAIAOQ6MVmF4fEzbQAAAIcAAAAUAAAAeGwvc2hhcmVkU3RyaW5ncy54bWw1yUEOAiEQRNG9pyAcwB5duDAMG09CxlZIphuki8TjSyaxVvXygxncV3a11Weg3YlsyyzJzrWxzvKqXRIm+5usdU5Py8yQna7LciNJRb3b6lCs/uLd0PIZ/Pg7ntyxYCUGRLAhEGKg6SPNZ4g/UEsDBBQAAAAIAOQ6MVniQK4SuQAAAD8CAAAaAAAAeGwvX3JlbHMvd29ya2Jvb2sueG1sLnJlbHOt0rEKgzAQBuDdp5A8gGctdCjq1MW17QsEPY2oSchdaX37ilirUIqDWZLj4P+/IfEVW8m10aRqS/6razUlQjHbMwDlCjtJgbGoh01pXCd5GF0FVuaNrBCiMDyBW2aI1POnMz/iZYufFYlwWXEQ/l26CjkRT+MaUohMMF5hMNQN697iFowpyzrHi8kfHWr+YYK5QMCH5/3XRV8dKemwuLGrdUV7y1bhm3XHhY77FvdnjakLz4SB1X9J31BLAwQUAAAACADkOjFZs67wLFEBAAAqBQAAEwAAAFtDb250ZW50X1R5cGVzXS54bWy9lMtOwzAQRff9iihbVLtiwQK13QBbQIIfcJ1J4tYv2dPX32NPEGqRo4gFzcaJ75y5147l5efZQ6xORtu4qntE/8h5lD0YEZnzYJPSumAEps/QcS/kTnTA7xeLBy6dRbA4x9yjXs8qemhYPkMr9hqrl1MqicrZVS0Oqq2rpwHKvqtamdyMBJ752Si8Mb7I5vkJtBux7aZdlXRF9GAbZpQMLroWWaqyU522HrpiKxImYG/LbJ6fQFG15dWTMAEfYVPedRIGePjpJTqAjr9o4b1WUmDSaQ+vT9j8+3SxRFJN7JWPd6lg8BozygXjPlf4sNS3A4SgGvhTONe2SkLj5N4khEUfQDSxB0CjGY3MCGUpbvUuAr4Kk7ryk+ZHF3Yb53bsJ8vsv4JkK3ofy0Fi5DQsbhAo4llDLKUZlFtE6EWA5gODsl05yWXBRSDKw+mKXH8BUEsDBBQAAAAIAOQ6MVlJryiUkQAAAPwAAAALAAAAX3JlbHMvLnJlbHONjzEOwjAMRXdOEeUAdWFgQGknlq4VFwip01ZN4sgJotyeCJaCGPD25a/3bNWj03mmkKY5JrF6F1Ijp5zjCSCZCb1OFUUMZWOJvc4l8ghRm0WPCIe6PgJvGbLdideoLVp0QyO5G/ZSXB4R/1GQtbPBM5mbx5B/mL4ahax5xNzI1cGdeLkSLVWBSnifpODj2fYJUEsBAhQDFAAAAAgA5DoxWR1G5mmnAAAAHAEAAA8AAAAAAAAAAAAAAIABAAAAAHhsL3dvcmtib29rLnhtbFBLAQIUAxQAAAAIAOQ6MVnxAZcjzgEAAEgKAAAYAAAAAAAAAAAAAACAAdQAAAB4bC93b3Jrc2hlZXRzL3NoZWV0MC54bWxQSwECFAMUAAAACADkOjFZSYxN3l8BAABOBAAADQAAAAAAAAAAAAAAgAHYAgAAeGwvc3R5bGVzLnhtbFBLAQIUAxQAAAAIAOQ6MVmF4fEzbQAAAIcAAAAUAAAAAAAAAAAAAACAAWIEAAB4bC9zaGFyZWRTdHJpbmdzLnhtbFBLAQIUAxQAAAAIAOQ6MVniQK4SuQAAAD8CAAAaAAAAAAAAAAAAAACAAQEFAAB4bC9fcmVscy93b3JrYm9vay54bWwucmVsc1BLAQIUAxQAAAAIAOQ6MVmzrvAsUQEAACoFAAATAAAAAAAAAAAAAACAAfIFAABbQ29udGVudF9UeXBlc10ueG1sUEsBAhQDFAAAAAgA5DoxWUmvKJSRAAAA/AAAAAsAAAAAAAAAAAAAAIABdAcAAF9yZWxzLy5yZWxzUEsFBgAAAAAHAAcAwgEAAC4IAAAAAA=='

    def test_documents_share_portal(self):
        spreadsheet = self.create_spreadsheet()
        response = self.url_open(spreadsheet.access_url)
        self.assertTrue(response.ok)

    @mute_logger('odoo.http')
    def test_documents_share_portal_wrong_token(self):
        self.create_spreadsheet()
        response = self.url_open("/odoo/documents/a-random-token")
        self.assertFalse(response.ok)

    def test_documents_share_portal_internal_redirect(self):
        spreadsheet = self.create_spreadsheet()
        new_test_user(self.env, login="raoul", password="Password!1")
        self.authenticate("raoul", "Password!1")
        response = self.url_open(spreadsheet.access_url)
        self.assertTrue(response.ok)
        self.assertIn("model=documents.document", response.url)
        self.assertIn(f"documents_init_document_id={spreadsheet.id}", response.url)

    def test_public_spreadsheet(self):
        spreadsheet = self.create_spreadsheet()
        response = self.url_open(spreadsheet.access_url)
        self.assertTrue(response.ok)

    @mute_logger('odoo.http')
    def test_public_spreadsheet_wrong_token(self):
        self.create_spreadsheet()
        response = self.url_open("/odoo/documents/a-random-token")
        self.assertFalse(response.ok)

    def test_contains_live_data_with_odoo_chart(self):
        spreadsheet_data = {
            "sheets": [
                {
                    "figures": [
                        {
                            "id": "1",
                            "x": 10,
                            "y": 10,
                            "width": 500,
                            "height": 300,
                            "tag": "chart",
                            "data": {
                                "title": {"text": "Documents"},
                                "metaData": {
                                    "groupBy": ["partner_id"],
                                    "measure": "id",
                                    "resModel": "documents.document",
                                },
                                "searchParams": {
                                    "context": {},
                                    "domain": '[]',
                                    "groupBy": [],
                                },
                                "type": "odoo_bar",
                            },
                        },
                    ],
                },
            ],
        }
        spreadsheet = self.create_spreadsheet({
            "spreadsheet_data": json.dumps(spreadsheet_data)
        })
        contains_live_data = spreadsheet._contains_live_data()
        self.assertTrue(contains_live_data)

    def test_public_spreadsheet_data(self):
        spreadsheet = self.create_spreadsheet()
        response = self.url_open(f"/documents/spreadsheet/{spreadsheet.access_token}")
        self.assertTrue(response.ok)
        self.assertEqual(response.json(), {'revisions': []})

    def test_public_spreadsheet_data_with_snapshot(self):
        spreadsheet = self.create_spreadsheet()
        snapshot_data = {"revisionId": "next-revision"}
        self.snapshot(
            spreadsheet, spreadsheet.current_revision_uuid, "next-revision", snapshot_data
        )
        response = self.url_open(f"/documents/spreadsheet/{spreadsheet.access_token}")
        self.assertTrue(response.ok)
        self.assertEqual(response.json(), {
            **snapshot_data,
            'revisions': []
        })

    def test_public_spreadsheet_get_revisions(self):
        spreadsheet = self.create_spreadsheet()
        revision_data = self.new_revision_data(spreadsheet)
        spreadsheet.dispatch_spreadsheet_message(revision_data)
        response = self.url_open(f"/documents/spreadsheet/{spreadsheet.access_token}")
        self.assertTrue(response.ok)
        self.assertEqual(len(response.json()['revisions']), 1)

    @mute_logger('odoo.http')
    def test_public_spreadsheet_data_wrong_token(self):
        self.create_spreadsheet()
        response = self.url_open("/documents/spreadsheet/a-random-token")
        self.assertFalse(response.ok)

    def test_download_document(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.handler = 'frozen_spreadsheet'
        spreadsheet.excel_export = self.EXCEL_EXPORT
        response = self.url_open(f"/documents/content/{spreadsheet.access_token}")

        self.assertTrue(response.ok)
        with ZipFile(BytesIO(response.content)) as zip_file:
            self.assertIn(b"test", zip_file.open(zip_file.filelist[3]).read())

    @mute_logger('odoo.http')
    def test_download_document_wrong_token(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.handler = 'frozen_spreadsheet'
        spreadsheet.excel_export = self.EXCEL_EXPORT
        response = self.url_open("/documents/content/a-random-token")
        self.assertFalse(response.ok)

    @freeze_time('01-01-2024 00:00:00')
    def test_download_all_document(self):
        spreadsheet = self.create_spreadsheet()
        folder = spreadsheet.folder_id
        self.assertTrue(folder)
        folder.access_via_link = 'view'
        self.share_spreadsheet(spreadsheet)

        response = self.url_open(f"/documents/content/{folder.access_token}")
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(response.content)) as zip_file:
            self.assertEqual(zip_file.namelist(), [
                'Frozen at 2024-01-01: Untitled Spreadsheet.xlsx',
            ])
            with ZipFile(BytesIO(zip_file.open(zip_file.filelist[0]).read())) as zip_file:
                sharedStrings = zip_file.filelist[3]
                assert sharedStrings.filename == 'xl/sharedStrings.xml'
                with zip_file.open(sharedStrings) as shared_strings_file:
                    self.assertIn(b"test", shared_strings_file.read())

    @mute_logger('odoo.http')
    def test_share_portal_document_folder_deletion(self):
        spreadsheet = self.create_spreadsheet()
        self.share_spreadsheet(spreadsheet)

        access_url = spreadsheet.access_url
        res = self.url_open(access_url)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)

        folder = spreadsheet.folder_id
        spreadsheet.action_archive()
        folder.action_archive()
        res = self.url_open(access_url)
        self.assertEqual(res.status_code, 404)

    def share_spreadsheet(self, spreadsheet):
        frozen_spreadsheet = spreadsheet.action_freeze_and_copy(b"{}", [])
        frozen_spreadsheet.excel_export = self.EXCEL_EXPORT
        frozen_spreadsheet.folder_id = spreadsheet.folder_id
        frozen_spreadsheet.is_access_via_link_hidden = False
        return frozen_spreadsheet
