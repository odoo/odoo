from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestConfig(TransactionCase):
    def test_evidence_types_seeded(self):
        codes = self.env["od19.billing.evidence.type"].search(
            [("name", "in", ["delivery_note", "vendor_tax_invoice"])]
        )
        self.assertEqual(len(codes), 2)

    def test_ar_mode_resolution_order(self):
        company = self.env.company
        company.od19_ar_billing_mode_default = "direct"
        partner = self.env["res.partner"].create({"name": "Mode Partner"})
        request = self.env["od19.billing.request"].create(
            {"direction": "ar", "partner_id": partner.id}
        )
        self.assertEqual(request.ar_billing_mode, "direct")
        partner.od19_ar_billing_mode = "two_step"
        request._compute_ar_billing_mode()
        self.assertEqual(request.ar_billing_mode, "two_step")

    def test_ap_original_flag_defaults_on(self):
        self.assertTrue(self.env.company.od19_ap_require_original)
