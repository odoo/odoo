from odoo.tests import tagged
from odoo.tests.common import TransactionCase

@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestDownloadXsds(TransactionCase):
    def test_download_xsds(self):
        self.env['ir.attachment'].action_download_xsd_files()
