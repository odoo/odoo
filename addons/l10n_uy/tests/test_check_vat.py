from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class CheckUyVat(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="uy"):
        super().setUpClass(chart_template_ref=chart_template_ref)

    @classmethod
    def _create_partner(cls, identification_type, vat):
        return cls.env["res.partner"].create({
            "name": "Uruguayan Partner",
            "l10n_latam_identification_type_id": cls.env.ref(f"l10n_uy.{identification_type}").id,
            "vat": vat,
            "country_id": cls.env.ref("base.uy").id
        })

    def test_valid_ci(self):
        # Valid CI
        partner = self._create_partner("it_ci", "3:402.010-1")
        self.assertTrue(partner._l10n_uy_ci_nie_is_valid())

        partner = self._create_partner("it_ci", "3 402 010 1")
        self.assertTrue(partner._l10n_uy_ci_nie_is_valid())

        partner = self._create_partner("it_ci", "34020101")
        self.assertTrue(partner._l10n_uy_ci_nie_is_valid())

    def test_valid_nie(self):
        partner = self._create_partner("it_nie", "93:402.010-1")
        self.assertTrue(partner._l10n_uy_ci_nie_is_valid())

        partner = self._create_partner("it_nie", "934020101")
        self.assertTrue(partner._l10n_uy_ci_nie_is_valid())

        partner = self._create_partner("it_nie", "93 402 010 1")
        self.assertTrue(partner._l10n_uy_ci_nie_is_valid())

    def test_valid_rut(self):
        self._create_partner("it_rut", "215521750017")
        self._create_partner("it_rut", "21-55217500-17")
        self._create_partner("it_rut", "21 55217500 17")
        self._create_partner("it_rut", "UY215521750017")

    def test_invalid_ci(self):
        common_msg = "The CI/NIE number.*does not seem to be valid"
        with self.assertRaisesRegex(ValidationError, common_msg, msg="not valid verification digit"):
            self._create_partner("it_ci", "3:402.010-2")
        with self.assertRaisesRegex(ValidationError, common_msg, msg="should not contain letters"):
            self._create_partner("it_ci", " ABC 3:402  asas .010-1")

    def test_invalid_nie(self):
        common_msg = "The CI/NIE number.*does not seem to be valid"
        with self.assertRaisesRegex(ValidationError, common_msg, msg="not valid verification digit"):
            self._create_partner("it_nie", "93:402.010-2")
        with self.assertRaisesRegex(ValidationError, common_msg, msg="should not contain letters"):
            self._create_partner("it_nie", "ABC 93:402. asas 010-1")

    def test_invalid_rut(self):
        common_msg = "The RUT number.*does not seem to be valid."
        with self.assertRaisesRegex(ValidationError, common_msg, msg="invalid number"):
            self._create_partner("it_rut", "215521750018")
        with self.assertRaisesRegex(ValidationError, common_msg, msg="do not accept dot ('.') character"):
            self._create_partner("it_rut", "21.55217500.17")
        with self.assertRaisesRegex(ValidationError, common_msg, msg="should not contain letters"):
            self._create_partner("it_rut", "2155 ABC 21750017")

        with self.assertRaisesRegex(ValidationError, common_msg, msg="Validation not working with generic VAT id type"):
            self.env["res.partner"].create({
                "name": "Uruguayan Partner",
                "country_id": self.env.ref("base.uy").id,
                "l10n_latam_identification_type_id": self.env.ref("l10n_latam_base.it_vat").id,
                "vat": "215521750018",
            })
