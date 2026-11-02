from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestCore(TransactionCase):
    def test_create_ar_request_gets_sequence(self):
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        self.assertTrue(request.name.startswith("BRI/AR/"))
        self.assertEqual(request.state, "draft")

    def test_create_ap_request_gets_sequence(self):
        request = self.env["od19.billing.request"].create({"direction": "ap"})
        self.assertTrue(request.name.startswith("BRI/AP/"))

    def test_move_type_follows_direction(self):
        ar = self.env["od19.billing.request"].create({"direction": "ar"})
        ap = self.env["od19.billing.request"].create({"direction": "ap"})
        self.assertEqual(ar.move_type, "out_invoice")
        self.assertEqual(ap.move_type, "in_invoice")
