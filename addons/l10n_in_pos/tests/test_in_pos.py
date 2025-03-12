from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n', 'l10n_pos_test')
class TestGenericIN(TestGenericLocalization):

    def setUp(self):
        super().setUp()
        self.state_in_gj = self.env.ref('base.state_in_gj')
        self.main_pos_config.company_id.write({
            'name': "Default Company",
            'state_id': self.state_in_gj.id,
            'vat': "24AAGCC7144L6ZE",
            'street': "Khodiyar Chowk",
            'street2': "Sala Number 3",
            'city': "Amreli",
            'zip': "365220",
        })
        self.main_pos_config.company_id.country_id = self.env.ref('base.in')
