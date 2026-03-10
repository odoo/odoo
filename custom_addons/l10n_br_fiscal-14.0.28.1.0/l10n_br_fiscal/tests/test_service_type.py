# @ 2018 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestServiceType(TransactionCase):
    def test_name_get(self):
        """Test Service Type name_get()"""
        self.service_type = self.env["l10n_br_fiscal.service.type"].create(
            {"code": "TESTE", "name": "TESTE", "internal_type": "normal"}
        )
        assert self.service_type.name_get(), "Error with function name_get()"
