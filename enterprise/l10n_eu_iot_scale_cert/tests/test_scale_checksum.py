import re

from odoo.tests import HttpCase
from odoo.tests.common import tagged
from odoo.addons.l10n_eu_iot_scale_cert.controllers.expected_checksum import EXPECTED_CHECKSUM


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestScaleChecksum(HttpCase):
    def test_checksum_matches_expected(self):
        self.authenticate("admin", "admin")

        response = self.url_open("/scale_checksum")
        self.assertEqual(response.status_code, 200)

        checksum_match = re.search(r"GLOBAL HASH: (\S+)", response.text)
        self.assertIsNotNone(checksum_match)
        self.assertEqual(checksum_match[1], EXPECTED_CHECKSUM)
