# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class Testl10nFrPosCert(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.main_pos_config.company_id
        company.country_id = cls.env.ref("base.fr")
        company.point_of_sale_use_ticket_qr_code = True
        company.point_of_sale_ticket_portal_url_display_mode = 'qr_code_and_url'


@tagged("post_install_l10n", "post_install", "-at_install")
class TestUi(Testl10nFrPosCert):
    def test_pos_use_ticket_qr_code_for_fr(self):
        company = self.main_pos_config.company_id
        self.assertEqual(company.country_id.code, "FR", "Company should be set to France (FR)")
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10nFrPosCertSelfInvoicingTour", login="pos_user")
