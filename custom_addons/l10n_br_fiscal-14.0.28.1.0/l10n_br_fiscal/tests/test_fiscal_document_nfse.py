# @ 2020 KMEE - www.kmee.com.br
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestFiscalDocumentNFSe(TransactionCase):
    def setUp(self):
        super().setUp()

        self.nfse_same_state = self.env.ref("l10n_br_fiscal.demo_nfse_same_state")

    def test_nfse_same_state(self):
        """Test NFSe same state."""

        self.nfse_same_state._onchange_document_serie_id()
        self.nfse_same_state._onchange_fiscal_operation_id()

        for line in self.nfse_same_state.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            self.assertEqual(
                line.fiscal_operation_line_id.name,
                "Prestação de Serviço",
                "Error to mappping Prestação de Serviço"
                " for Venda de Serviço de Contribuinte Dentro do Estado.",
            )

            # Service Type
            self.assertEqual(
                line.service_type_id.code,
                "1.05",
                "Error to mapping Service Type Code 1.05"
                " for Venda de Serviço de Contribuinte Dentro do Estado.",
            )

            # ISSQN
            self.assertEqual(
                line.issqn_tax_id.name,
                "ISSQN 5%",
                "Error to mapping ICMS CST Tributada com permissão de crédito"
                " for Venda de Serviço de Contribuinte Dentro do Estado.",
            )
