from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericIN(TestGenericLocalization):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        cls.state_in_gj = cls.env.ref('base.state_in_gj')
        cls.main_pos_config.company_id.write({
            'name': "Default Company",
            'state_id': cls.state_in_gj.id,
            'vat': "24AAGCC7144L6ZE",
            'street': "Khodiyar Chowk",
            'street2': "Sala Number 3",
            'city': "Amreli",
            'zip': "365220",
        })
        cls.whiteboard_pen.write({
            'l10n_in_hsn_code': '1111',
        })

        cls.wall_shelf.write({
            'l10n_in_hsn_code': '2222',
        })

    def test_generic_localization(self):
        _, html = super().test_generic_localization()
        self.assertTrue("HSN Code" in html)
        self.assertTrue("Tax Invoice" in html)
