from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class CheckUyVat(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('uy')
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def _create_partner_with_rut(cls, vat):
        return cls.env["res.partner"].create({
            "name": "Uruguayan Partner",
            "vat": vat,
            "country_id": cls.env.ref("base.uy").id,
        })

    @classmethod
    def _create_partner_with_identifier(cls, identifier_type, value):
        return cls.env["res.partner"].create({
            "name": "Uruguayan Partner",
            "additional_identifiers": {identifier_type: value},
            "country_id": cls.env.ref("base.uy").id,
        })

    def test_valid_ci(self):
        # Valid CI (canonical and a few accepted separator variants)
        for value in ("3:402.010-1", "3 402 010 1", "34020101"):
            self._create_partner_with_identifier("UY_CI", value)

    def test_valid_nie(self):
        for value in ("93:402.010-1", "934020101", "93 402 010 1"):
            self._create_partner_with_identifier("UY_NIE", value)

    def test_valid_rut(self):
        for value in ("215521750017", "21-55217500-17", "21 55217500 17", "UY215521750017"):
            self._create_partner_with_rut(value)

    def test_invalid_ci(self):
        # Bad checksum and non-numeric content are both rejected
        with self.assertRaises(ValidationError, msg="not valid verification digit"):
            self._create_partner_with_identifier("UY_CI", "3:402.010-2")
        with self.assertRaises(ValidationError, msg="should not contain letters"):
            self._create_partner_with_identifier("UY_CI", " ABC 3:402  asas .010-1")

    def test_invalid_nie(self):
        with self.assertRaises(ValidationError, msg="not valid verification digit"):
            self._create_partner_with_identifier("UY_NIE", "93:402.010-2")
        with self.assertRaises(ValidationError, msg="should not contain letters"):
            self._create_partner_with_identifier("UY_NIE", "ABC 93:402. asas 010-1")

    def test_invalid_rut(self):
        with self.assertRaises(ValidationError, msg="invalid number"):
            self._create_partner_with_rut("215521750018")
        with self.assertRaises(ValidationError, msg="do not accept dot ('.') character"):
            self._create_partner_with_rut("21.55217500.17")
        with self.assertRaises(ValidationError, msg="should not contain letters"):
            self._create_partner_with_rut("2155 ABC 21750017")
