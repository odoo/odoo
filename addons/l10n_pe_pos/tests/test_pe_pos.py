from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericPE(TestGenericLocalization):
    pos_partner_pos_form_fields = ['l10n_latam_identification_type_id', 'l10n_pe_district']

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()
