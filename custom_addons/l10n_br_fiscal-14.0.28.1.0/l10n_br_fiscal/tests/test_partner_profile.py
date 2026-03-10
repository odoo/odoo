# @ 2018 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPartnerFiscalProfile(TransactionCase):
    def test_create_other_default_type(self):
        default_type = self.env["l10n_br_fiscal.partner.profile"].search(
            [("default", "=", True)]
        )
        assert default_type, "The data of Partner Fiscal Type not loaded."
        with self.assertRaises(ValidationError):
            self.env["l10n_br_fiscal.partner.profile"].create(
                {"code": "TESTE", "default": True, "is_company": True}
            )
