# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_invoice.tests.common import TestPhInvoiceCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPartnerPrivilegeIdentifiers(TestPhInvoiceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Juan dela Cruz",
            "country_id": cls.env.ref("base.ph").id,
            "additional_identifiers": {"PH_PWD_ID": "PWD-123", "PH_SC_ID": "SC-456"},
        })
        account = cls.company_data["default_account_revenue"]
        Privilege = cls.env["l10n_ph.discount.privilege"].sudo()
        cls.pwd_privilege, cls.sc_privilege, cls.special_privilege = Privilege.create([
            {"name": name, "discount_type": discount_type, "discount_amount": 0.2, "account_id": account.id}
            for name, discount_type in (("PWD", "pwd"), ("SC", "sc"), ("Special", "special"))
        ])
        cls.product = cls.env["product.product"].create({"name": "Office Lamp", "list_price": 100.0})

    def _create_partner_invoice(self, partner=None, **kwargs):
        return self._create_invoice_with_lines(
            ("Lamp", self.product, 100.0),
            partner_id=(partner or self.partner).id,
            **kwargs,
        )

    def test_identifiers_available_for_ph_contacts(self):
        keys = {
            "PH_PWD_ID",
            "PH_SC_ID",
            "PH_NCAA_ID",
            "PH_SOLO_PARENT_ID",
            "PH_MEDAL_OF_VALOR_ID",
        }
        self.assertLessEqual(keys, set(self.partner.available_additional_identifiers_metadata))
        be_partner = self.partner.copy({"country_id": self.env.ref("base.be").id})
        self.assertFalse(keys & set(be_partner.available_additional_identifiers_metadata))

    def test_identifiers_are_not_synced_to_contacts(self):
        self.partner.is_company = True
        child = self.env["res.partner"].create({
            "name": "Child",
            "parent_id": self.partner.id,
            "country_id": self.env.ref("base.ph").id,
        })
        self.partner.additional_identifiers = {"PH_PWD_ID": "PWD-123"}
        self.assertEqual(self.partner.additional_identifiers, {"PH_PWD_ID": "PWD-123"})
        self.assertFalse(child.additional_identifiers)

    def test_invoice_privilege_id_is_filled_from_the_customer_id(self):
        invoice = self._create_partner_invoice()
        self.assertFalse(invoice.l10n_ph_privilege_id_no)

        self._apply_privilege(invoice, privilege_id=self.pwd_privilege.id, apply_on="all")
        self.assertEqual(invoice.l10n_ph_privilege_id_no, "PWD-123")

        sc_invoice = self._create_partner_invoice()
        self._apply_privilege(sc_invoice, privilege_id=self.sc_privilege.id, apply_on="all")
        self.assertEqual(sc_invoice.l10n_ph_privilege_id_no, "SC-456")

    def test_invoice_privilege_id_is_empty_for_a_special_discount(self):
        invoice = self._create_partner_invoice()
        self._apply_privilege(invoice, privilege_id=self.special_privilege.id, apply_on="all")
        self.assertFalse(invoice.l10n_ph_privilege_id_no)

    def test_typed_privilege_id_is_kept_without_matching_customer_id(self):
        invoice = self._create_partner_invoice(self.partner_a, l10n_ph_privilege_id_no="TYPED-1")
        self._apply_privilege(invoice, privilege_id=self.pwd_privilege.id, apply_on="all")
        self.assertEqual(invoice.l10n_ph_privilege_id_no, "TYPED-1")

    def test_customer_id_of_another_type_is_not_used(self):
        self.partner.additional_identifiers = {"PH_SC_ID": "SC-456"}
        invoice = self._create_partner_invoice()
        self._apply_privilege(invoice, privilege_id=self.pwd_privilege.id, apply_on="all")
        self.assertFalse(invoice.l10n_ph_privilege_id_no)

    def test_draft_follows_the_customer_id_but_posted_keeps_its_own(self):
        invoice = self._create_partner_invoice()
        self._apply_privilege(invoice, privilege_id=self.pwd_privilege.id, apply_on="all")

        self.partner.additional_identifiers = {"PH_PWD_ID": "PWD-200"}
        self.assertEqual(invoice.l10n_ph_privilege_id_no, "PWD-200")

        invoice.action_post()
        self.partner.additional_identifiers = {"PH_PWD_ID": "PWD-300"}
        self.assertEqual(invoice.l10n_ph_privilege_id_no, "PWD-200")
