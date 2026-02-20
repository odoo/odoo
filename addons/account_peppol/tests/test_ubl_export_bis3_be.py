from odoo.addons.account_edi_ubl_cii.tests.test_ubl_export_bis3_be import TestUblExportBis3BE
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblExportBis3BE.extra_tags)
class TestUblExportBis3BEPeppol(TestUblExportBis3BE):

    def test_invoice_PEPPOL_EN16931_R010_R020_ensure_customer_supplier_endpoint_id(self):
        """
        [PEPPOL-EN16931-R010] Buyer electronic address MUST be provided.
        [PEPPOL-EN16931-R020] Seller electronic address MUST be provided.
        """
        partner = self.env['res.partner'].create({
            **self._create_partner_default_values(),
            'name': "partner",
            'country_id': self.env.ref('base.be').id,
        })
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=10.0, taxes_id=tax_21)

        # Check customer's endpoint with Peppol.
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=partner,
            post=True,
        )
        with self.assertRaisesRegex(UserError, r".*\[PEPPOL\-EN16931\-R010\].*"):
            self._generate_invoice_ubl_file(invoice, sending_methods=['peppol'])

        # Check customer's endpoint without Peppol.
        self._generate_invoice_ubl_file(invoice)

        # Check supplier's endpoint with Peppol.
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=partner,
            post=True,
        )

        partner.peppol_eas = '0208'
        partner.peppol_endpoint = '0477472701'
        self.env.company.partner_id.vat = None
        self.env.company.partner_id.company_registry = None
        self.env.company.partner_id.peppol_eas = None
        self.env.company.partner_id.peppol_endpoint = None
        with self.assertRaisesRegex(UserError, r".*\[PEPPOL\-EN16931\-R020\].*"):
            self._generate_invoice_ubl_file(invoice, sending_methods=['peppol'])

        # Check supplier's endpoint without Peppol.
        self._generate_invoice_ubl_file(invoice)
