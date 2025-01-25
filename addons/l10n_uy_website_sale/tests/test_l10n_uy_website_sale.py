from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='uy'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_checkout_address_uy(self):
        self.env.company.country_id = self.env.ref('base.uy').id
        self.env['website'].get_current_website().company_id = self.env.company.id
        self.start_tour('/shop', 'shop_checkout_address_uy', login='accountman')
