from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ge_edi.tests import stub_responses
from odoo.addons.l10n_ge_edi.tests.common import RSGE_USER_ID, TestL10nGeEdiCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nGeEdiPartner(TestL10nGeEdiCommon):

    def test_fetch_un_id_without_credentials_raises_error(self):
        self.company.sudo().l10n_ge_edi_su = False

        with self.assertRaisesRegex(UserError, "RS.ge Service User"):
            self.partner_ge.action_l10n_ge_edi_fetch_un_id()

        self.assertFalse(self.partner_ge.l10n_ge_edi_un_id)

    def test_fetch_un_id_with_credentials(self):
        self._stub_rsge(get_un_id_from_tin=stub_responses.get_un_id_from_tin(un_id=1149251))

        self.assertEqual(self.rsge_user_id, RSGE_USER_ID)

        self.partner_ge.action_l10n_ge_edi_fetch_un_id()

        self.assertEqual(self.partner_ge.l10n_ge_edi_un_id, "1149251")

    def test_fetch_un_id_without_vat_skips_only_that_partner(self):
        partner_without_vat = self.env["res.partner"].create({
            "name": "No TIN Customer",
            "country_id": self.env.ref("base.ge").id,
        })
        self._stub_rsge(get_un_id_from_tin=stub_responses.get_un_id_from_tin(un_id=1149251))

        # the failing partner comes first, so aborting the loop would leave the second one unresolved
        (partner_without_vat + self.partner_ge).action_l10n_ge_edi_fetch_un_id()

        self.assertEqual(self.partner_ge.l10n_ge_edi_un_id, "1149251")
        self.assertFalse(partner_without_vat.l10n_ge_edi_un_id)

    def test_fetch_un_id_with_rsge_fault_leaves_un_id_unset(self):
        self._stub_rsge(get_un_id_from_tin=stub_responses.fault())

        self.partner_ge.action_l10n_ge_edi_fetch_un_id()

        self.assertFalse(self.partner_ge.l10n_ge_edi_un_id)
