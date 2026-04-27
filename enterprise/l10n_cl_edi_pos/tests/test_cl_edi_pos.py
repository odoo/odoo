from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericCL(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('cl')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.company_id.name = 'Company CL'
