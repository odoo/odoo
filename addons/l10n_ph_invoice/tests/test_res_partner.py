# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestResPartnerDiscountPrivilegeIdentifiers(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
    def setUpClass(cls):
        super().setUpClass()

    def test_privilege_ids_coexist_with_tin_and_stay_out_of_edi(self):
        """An individual SC/PWD customer usually has a TIN too: the privilege IDs
        must not trip the individual/company identifier check, and must never
        be picked as the partner's legal entity or tax identifier."""
        partner = self.env["res.partner"].create({
            "name": "Juan Dela Cruz",
            "country_id": self.env.ref("base.ph").id,
            "vat": "123-456-789-000",
            "additional_identifiers": {"PH_SC_ID": "SC-REG-001", "PH_PWD_ID": "PWD-REG-001"},
        })

        self.assertEqual(partner.additional_identifiers, {"PH_SC_ID": "SC-REG-001", "PH_PWD_ID": "PWD-REG-001"})
        self.assertLessEqual({"PH_SC_ID", "PH_PWD_ID"}, set(partner.available_additional_identifiers_metadata))
        self.assertNotIn(partner._get_preferred_legal_entity_identifier_vals().get("key"), {"PH_SC_ID", "PH_PWD_ID"})
        self.assertNotIn(partner._get_preferred_tax_identifier_vals().get("key"), {"PH_SC_ID", "PH_PWD_ID"})
