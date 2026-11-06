# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.tests import TransactionCase

IMAGE_GIF_B64 = b"R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

SPREADSHEET_DATA_WITH_B64_IMAGE = {
    "sheets": [
        {
            "id": "sheet1",
            "figures": [
                {
                    "id": "image1",
                    "x": 0,
                    "y": 0,
                    "width": 193,
                    "height": 183,
                    "tag": "image",
                    "data": {
                        "path": "data:image/gif;base64," + IMAGE_GIF_B64.decode(),
                        "size": {"width": 193, "height": 183},
                        "mimetype": "image/gif",
                    },
                },
            ],
        },
    ],
}


class SpreadsheetImageTestMixin(TransactionCase):
    # Assertions shared by the tests of the models inheriting from spreadsheet.mixin.

    def assert_spreadsheet_image_in_db(self, record, expected_b64=IMAGE_GIF_B64, mimetype="image/gif"):
        related_image_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', record._name),
            ('res_id', '=', record.id),
            ('mimetype', '=', mimetype),
        ])
        self.assertEqual(len(related_image_attachment), 1)
        self.assertEqual(related_image_attachment.datas, expected_b64)
        figure = json.loads(record.spreadsheet_data)['sheets'][0]['figures'][0]
        self.assertEqual(figure['tag'], 'image')
        self.assertEqual(figure['data']['path'], f'/web/image/{related_image_attachment.id}')
        self.assertEqual(figure['data']['mimetype'], mimetype)
