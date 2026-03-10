# @ 2018 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestCNAE(TransactionCase):
    def test_name_get(self):
        """Test CNAE name_get()"""
        self.cnae = self.env["l10n_br_fiscal.cnae"].create(
            {
                "code": "TESTE",
                "name": "TESTE",
                "version": "TESTE",
                "internal_type": "normal",
            }
        )
        assert self.cnae.name_get(), "Error with function name_get()"
