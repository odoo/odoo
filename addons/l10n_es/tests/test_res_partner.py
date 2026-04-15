from odoo.tests import TransactionCase, tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nEs(TransactionCase):

    def setUp(self):
        super().setUp()

    def test_child_partner_has_no_vat(self):
        Partner = self.env["res.partner"]
        partner = Partner.create({"name": "parent", "vat": "A1235567Y", "country_code": "ES"})
        child = Partner.create({"name": "child", "parent_id": partner.id})
        self.assertTrue(partner.is_company, "partner who own commercial entity should be company")
        self.assertFalse(child.is_company, "child partner is not company")
