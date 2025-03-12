from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericES(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.l10n_es_simplified_invoice_journal_id = cls.main_pos_config.journal_id
