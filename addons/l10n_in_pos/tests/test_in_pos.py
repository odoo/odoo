# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nInPos(TestPointOfSaleHttpCommon):

    @classmethod
    @TestPointOfSaleHttpCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        cls.magnetic_board.write({'l10n_in_hsn_code': 1234})

    def test_pos_receipt_with_hsn_summary(self):
        """ Test PoS receipt displays HSN summary when a product with an HSN code is added. """
        self.main_pos_config.open_ui()
        self.start_pos_tour('ReceiptWithHSNSummaryTour', login="accountman")
        last_order = self.env['pos.order'].search([], limit=1, order='id desc')
        self.assertEqual(last_order.state, 'paid', "The last order should be paid successfully.")
