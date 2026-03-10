# Copyright (C) 2022-Today - Engenere (<https://engenere.one>).
# @author Antônio S. Pereira Neto <neto@engenere.one>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import SavepointCase
from odoo.tools import mute_logger


class ValidCreatePIXTest(SavepointCase):
    """Test if ValidationError is raised well during create({})"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.res_partner_pix_model = cls.env["res.partner.pix"]
        cls.partner_id = cls.env.ref("l10n_br_base.res_partner_amd")

    def test_invalid_pix_cnpj_too_big(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "cnpj_cpf",
            "key": "0296089500013199",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_cnpj_too_less(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "cnpj_cpf",
            "key": "950001319",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_cnpj_wrong_value(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "cnpj_cpf",
            "key": "12345897560234",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_phone_wrong_value(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "phone",
            "key": "1103252020",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_phone_wrong_country_code(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "phone",
            "key": "0119991123456789",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_email_wrong_value(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "email",
            "key": "teste#teste.com",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_email_too_long(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "email",
            "key": "toooooooolooooooooooongemaaaaaailllllll@teeeeeeeee"
            "eeeeeeeeeeeeeeeeeeeest.com.br",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_EVP_wrong_value(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "evp",
            "key": "nmmnaasa-qwhjwqhjk-2112",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_EVP_wrong_blocks(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "evp",
            "key": "123e4567-e12b-12d1-a456-426655-40000",
        }
        self.check_validation_error_on_create(pix_vals)

    def test_invalid_pix_EVP_wrong_hex(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "evp",
            "key": "123*4567-e12b-12d1-a456-426655440000",
        }
        self.check_validation_error_on_create(pix_vals)

    def check_validation_error_on_create(self, pix_vals):
        with self.assertRaises(ValidationError):
            self.res_partner_pix_model.with_context(tracking_disable=True).create(
                pix_vals
            )

    def test_repeated_pix_key(self):
        pix_vals = {
            "partner_id": self.partner_id.id,
            "key_type": "phone",
            "key": "+50372424737",
        }
        self.res_partner_pix_model.with_context(tracking_disable=True).create(pix_vals)
        with mute_logger("odoo.sql_db"):
            with self.assertRaisesRegex(IntegrityError, "partner_pix_key_unique"):
                self.res_partner_pix_model.with_context(tracking_disable=True).create(
                    pix_vals
                )
