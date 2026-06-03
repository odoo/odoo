from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericUY(TestGenericLocalization):
    pos_partner_pos_form_fields = ['l10n_latam_identification_type_id']

    @classmethod
    @AccountTestInvoicingCommon.setup_country('uy')
    def setUpClass(cls):
        super().setUpClass()
