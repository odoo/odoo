from odoo.tests import tagged

from odoo.addons.l10n_fr_pdp.tests.common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpLatePaymentPenaltyNotes(TestL10nFrPdpCommon):

    def test_ubl_uses_company_late_payment_penalties_rate(self):
        self.company.write({
            'l10n_fr_pdp_manual_late_payment_penalties_rate': 12.4,
            'l10n_fr_pdp_late_payment_penalties_automatic': False,
        })
        invoice = self._create_french_invoice()
        invoice.action_post()

        wizard = self.create_send_and_print(invoice, checkbox_ubl_cii_xml=True)
        wizard.action_send_and_print()

        self.assertTrue(invoice.ubl_cii_xml_id)
        self.assertIn(
            b"#PMD#Late payment penalties at an annual rate of 12.40%",
            invoice.ubl_cii_xml_id.raw,
        )
        self.assertIn(b"#PMT#In the event of late payment", invoice.ubl_cii_xml_id.raw)
        self.assertIn(b"#AAB#", invoice.ubl_cii_xml_id.raw)
