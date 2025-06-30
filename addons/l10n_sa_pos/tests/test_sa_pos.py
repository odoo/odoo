# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):

    def test_sa_qr_in_right_timezone(self):
        """
        Tests that the Saudi Arabia's timezone is applied on the QR code generated at the
        end of an order.
        """
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_sa_qr_in_right_timezone', login="pos_admin")
