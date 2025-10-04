# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.exceptions import ValidationError


class TestUnsplash(common.TransactionCase):
    def test_constraint(self):
        self.env["ir.attachment"].create(
            {
                "name": "attachment",
                "url": "/unsplash/xyz",
                "datas": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            },
        )

        with self.assertRaises(ValidationError):
            self.env["ir.attachment"].create(
                {
                    "name": "attachment",
                    "url": "/unsplash/xyz",
                    "datas": "dGVzdA==",
                },
            )
