# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

SIRET = '73282932000074'
SIREN = '732829320'
IDENTIFIERS_XPATH = "//div[starts-with(normalize-space(.), 'SIRET:') or starts-with(normalize-space(.), 'SIREN:')]"


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReportInvoice(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()
        # The customer address is printed in the address block of the standard layout.
        cls.env.company.external_report_layout_id = cls.env.ref('web.external_layout_standard')
        cls.partner_a.write({
            'country_id': cls.env.ref('base.fr').id,
            'company_registry': SIRET,
            'lang': 'en_US',  # the "SIRET:" and "SIREN:" labels are translated in French
        })

    def _check_invoice_identifiers(self):
        """ Check that the customer SIRET and SIREN are printed once, under the customer address,
        in the three customer address blocks of the invoice report.
        """
        expected = [['SIRET:', SIRET], ['SIREN:', SIREN]]
        invoice = self._create_invoice()
        self.assertTrue(invoice.l10n_fr_is_company_french)
        for shipping_partner, address_block in (
            (self.env['res.partner'], 'no_shipping'),
            (self.partner_a, 'address_same_as_shipping'),
            (self.partner_b, 'address_not_same_as_shipping'),
        ):
            with self.subTest(address_block=address_block):
                invoice.partner_shipping_id = shipping_partner
                report = self.env['ir.actions.report']._render_qweb_html('account.report_invoice', invoice.ids)[0]
                tree = html.fromstring(report)
                self.assertTrue(tree.xpath('//div[@name=$name]', name=address_block))
                customer_address = tree.xpath("//div[@name='address']")
                self.assertEqual(len(customer_address), 1)
                identifiers = [node.text_content().split() for node in tree.xpath(IDENTIFIERS_XPATH)]
                identifiers_under_address = [
                    node.text_content().split() for node in customer_address[0].xpath('.' + IDENTIFIERS_XPATH)
                ]
                self.assertEqual(identifiers_under_address, expected)
                self.assertEqual(identifiers, expected)

    def test_invoice_identifiers(self):
        self._check_invoice_identifiers()

    def test_invoice_identifiers_with_extra_addresses(self):
        # Mimic l10n_din5008.report_invoice_document: a view applied before the French one
        # inserts addresses before the standard address blocks.
        self.env['ir.ui.view'].create({
            'name': 'account.report_invoice_document.inherit.extra_addresses',
            'type': 'qweb',
            'inherit_id': self.env.ref('account.report_invoice_document').id,
            'priority': self.env.ref('l10n_fr_account.report_invoice_document').priority - 1,
            'arch_db': '''
                <xpath expr="//t[@t-set='forced_vat']" position="after">
                    <t t-set="extra_addresses">
                        <address/>
                        <address/>
                    </t>
                </xpath>
            ''',
        })
        self._check_invoice_identifiers()
