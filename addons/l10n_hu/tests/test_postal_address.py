# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nHuPostalAddress(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('hu')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.write({
            'street': 'Nador utca 7.',
            'zip': '1051',
            'city': 'Budapest',
            'country_id': cls.env.ref('base.hu').id,
        })
        cls.invoice = cls._create_invoice(post=True)

    def _printed_address(self):
        # The address is computed outside of the report first: the report must not reuse it.
        self.invoice.partner_id.with_context(show_address=True, lang='en_US').display_name
        report = html.fromstring(self.env['ir.actions.report']._render_qweb_html('account.account_invoices', self.invoice.ids)[0])
        return [line.strip() for line in report.xpath("//div[@name='address']//address//text()") if line.strip()]

    def test_postal_address_light_layout(self):
        self.env.company.external_report_layout_id = self.env.ref('web.external_layout_standard')
        self.assertEqual(self._printed_address(), ['partner_a', 'Budapest', 'Nador utca 7.', '1051'])

    def test_address_other_layouts(self):
        self.env.company.external_report_layout_id = self.env.ref('web.external_layout_bubble')
        self.assertEqual(self._printed_address(), ['partner_a'] + self.partner_a._display_address(without_name=True).splitlines())
        self.assertNotEqual(self._printed_address()[-1], '1051')
