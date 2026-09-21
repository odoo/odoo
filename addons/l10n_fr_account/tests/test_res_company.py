from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrAccountResCompany(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('fr_comp')
    def setUpClass(cls):
        super().setUpClass()

    def test_disable_vat(self):
        self.assertEqual(
            self.company.account_purchase_tax_id,
            self.env['account.chart.template'].with_company(self.company).ref('tva_acq_normale', raise_if_not_found=False),
        )
        self.company.vat_disabled = True
        self.assertEqual(
            self.company.account_purchase_tax_id,
            self.env['account.chart.template'].with_company(self.company).ref('tva_purchase_na_normale_biens', raise_if_not_found=False),
        )
