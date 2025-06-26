from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_in.tests.test_hsn_summary import TestL10nInHSNSummary
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nInHSNSummaryPos(TestTaxCommonPOS, TestL10nInHSNSummary):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()

    def create_base_line_product(self, base_line, **kwargs):
        # OVERRIDE 'point_of_sale'
        return super().create_base_line_product(base_line, **kwargs, l10n_in_hsn_code=base_line['l10n_in_hsn_code'])

    def test_l10n_in_hsn_summary_pos(self):
        # We only do the first test just to be sure the code is not crashing.
        # There is no custom code in the POS for that so we suppose the results
        # are exactly the same.
        tests = self._test_l10n_in_hsn_summary_1()
        test1 = next(tests)
        self.ensure_products_on_document(test1[1], 'product_1')
        with self.with_new_session(user=self.pos_user):
            self.start_pos_tour('test_l10n_in_hsn_summary_pos')
