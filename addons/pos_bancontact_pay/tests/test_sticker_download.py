import io
from unittest.mock import patch

from PIL import Image

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


@tagged("post_install", "-at_install")
class TestStickerDownload(TestBancontactPay):
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super().setUp()
        self.authenticate("pos_admin", "pos_admin")

    def test_download_sticker(self):
        qr = io.BytesIO()
        Image.new("RGBA", (10, 10), "black").save(qr, format="PNG")

        with patch("odoo.addons.pos_bancontact_pay.models.pos_bancontact_sticker.PosBancontactSticker._fetch_sticker_image", return_value=qr.getvalue()):
            response = self.url_open(f"/bancontact_pay/sticker/{self.bancontact_sticker_1.identifier}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/png")
        self.assertEqual(response.headers["Content-Disposition"], "attachment; filename*=UTF-8''Sticker%201.png")

    @mute_logger("odoo.http")
    def test_download_sticker_unknown_identifier(self):
        response = self.url_open("/bancontact_pay/sticker/unknown")
        self.assertEqual(response.status_code, 404)
