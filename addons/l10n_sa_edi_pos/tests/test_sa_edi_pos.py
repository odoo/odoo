from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n', 'l10n_pos_test')
class TestGenericSAEdi(TestGenericLocalization):
    def setUp(self):
        super().setUp()
        self.main_pos_config.company_id.country_id = self.env.ref('base.sa')
        self.main_pos_config.company_id.name = 'Generic SA EDI'
