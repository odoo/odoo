from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged
from unittest.mock import patch


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericESTbai(TestGenericLocalization):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.l10n_es_tbai_tax_agency = 'bizkaia'

    def test_generic_localization(self):
        # The TicketBAI QR code is only printed once the tax agency accepted the document,
        # which is not sent during the tour: simulate its URL. A plain function, as the POS
        # calls the method by RPC, which a mock object would not pass.
        def get_l10n_es_pos_tbai_qrurl(order):
            return 'https://batuz.eus/QRTBAI/?id=TBAI-TEST'

        with patch.object(self.env.registry['pos.order'], 'get_l10n_es_pos_tbai_qrurl', get_l10n_es_pos_tbai_qrurl):
            _, html = super().test_generic_localization()
        self.assertTrue("TicketBai QR Code" in html)
