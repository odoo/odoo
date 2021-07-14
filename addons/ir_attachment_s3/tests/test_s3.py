# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License MIT (https://opensource.org/licenses/MIT).

import base64
import unittest
from urllib.parse import urlparse

import requests

from odoo.tests.common import TransactionCase, tagged


@tagged("at_install", "post_install")
class TestS3(TransactionCase):
    def _check_url_content(self, attachment, datas):
        o = urlparse(attachment.url)
        self.assertEqual(o.scheme, "https")
        self.assertTrue(o.netloc.endswith(".s3.amazonaws.com"))

        r = requests.get(attachment.url, timeout=5)
        r.raise_for_status()
        self.assertEqual(datas, base64.b64encode(r.content))

    def test_main(self):

        try:
            self.env["res.config.settings"].get_s3_bucket()
        except Exception as e:
            raise unittest.SkipTest(str(e))

        white_pixel = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        attachment = (
            self.env["ir.attachment"]
            .with_context(force_s3=True)
            .create({"name": "Attachment", "datas": white_pixel})
        )

        self._check_url_content(attachment, white_pixel)

        red_pixel = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5AYFCS4qJvIN0wAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAADElEQVQI12P4z8AAAAMBAQAY3Y2wAAAAAElFTkSuQmCC"
        attachment.write({"datas": red_pixel})
        self._check_url_content(attachment, red_pixel)
