from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n', 'l10n_pos_test')
class TestGenericES(TestGenericLocalization):
    def setUp(self):
        super().setUp()
        self.main_pos_config.company_id.country_id = self.env.ref('base.es')
        self.main_pos_config.l10n_es_simplified_invoice_journal_id = self.main_pos_config.journal_id
