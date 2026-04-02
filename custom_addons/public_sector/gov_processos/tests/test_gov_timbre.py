import base64
import io
import unittest
from unittest.mock import patch

from odoo.addons.gov_processos.models import gov_timbre
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGovTimbre(TransactionCase):
    @staticmethod
    def _fake_png_b64(size_bytes):
        raw = b"\x89PNG\r\n\x1a\n" + (b"x" * max(size_bytes - 8, 0))
        return base64.b64encode(raw).decode("ascii")

    @staticmethod
    def _png_b64(size, color=(30, 90, 180, 255)):
        buffer = io.BytesIO()
        image = gov_timbre.Image.new("RGBA", size, color)
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _image_size(b64_data):
        with gov_timbre.Image.open(io.BytesIO(base64.b64decode(b64_data))) as image:
            return image.size, image.format

    def test_cabecalho_accepts_file_above_15mb(self):
        payload = self._fake_png_b64((15 * 1024 * 1024) + 1024)

        with patch.object(gov_timbre, "_PIL_AVAILABLE", False):
            self.env["gov.timbre"]._validate_image(
                payload,
                max_bytes=gov_timbre.CABECALHO_MAX_BYTES,
                max_width=gov_timbre.CABECALHO_MAX_WIDTH,
                max_height=gov_timbre.CABECALHO_MAX_HEIGHT,
                label="cabecalho",
            )

    @unittest.skipUnless(gov_timbre._PIL_AVAILABLE, "Pillow required for image resizing")
    def test_create_resizes_cabecalho_to_fit_layout(self):
        timbre = self.env["gov.timbre"].create(
            {
                "name": "Timbre com cabecalho grande",
                "ug_id": self.env.company.id,
                "cabecalho_img": self._png_b64((2048, 2048)),
            }
        )

        (width, height), image_format = self._image_size(timbre.cabecalho_img)
        self.assertEqual(image_format, "PNG")
        self.assertEqual((width, height), (200, 200))

    @unittest.skipUnless(gov_timbre._PIL_AVAILABLE, "Pillow required for image resizing")
    def test_write_resizes_rodape_to_fit_layout(self):
        timbre = self.env["gov.timbre"].create(
            {
                "name": "Timbre com rodape grande",
                "ug_id": self.env.company.id,
            }
        )

        timbre.write({"rodape_img": self._png_b64((1600, 400))})

        (width, height), image_format = self._image_size(timbre.rodape_img)
        self.assertEqual(image_format, "PNG")
        self.assertEqual((width, height), (400, 100))

    def test_cabecalho_rejects_file_above_16mb_limit(self):
        payload = self._fake_png_b64(gov_timbre.CABECALHO_MAX_BYTES + 1)

        with self.assertRaisesRegex(ValidationError, r"16 MB"):
            self.env["gov.timbre"]._validate_image(
                payload,
                max_bytes=gov_timbre.CABECALHO_MAX_BYTES,
                max_width=gov_timbre.CABECALHO_MAX_WIDTH,
                max_height=gov_timbre.CABECALHO_MAX_HEIGHT,
                label="cabecalho",
            )
