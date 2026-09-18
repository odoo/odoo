from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged

from .common import TestL10nEsEdiVerifactuPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuPosFrontend(TestL10nEsEdiVerifactuPosCommon, TestPointOfSaleHttpCommon):

    def test_simplified_invoice_on_receipt(self):
        """
        Tests that the simplified invoice is on the receipt if needed
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self._mock_zeep_registration_operation_certificate_issue():
            self.start_tour(
                f'/pos/ui?config_id={self.main_pos_config.id}',
                'l10n_es_edi_verifactu_pos.test_simplified_invoice_on_receipt',
                login='pos_user'
            )
