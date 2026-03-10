# @ 2020 KMEE - www.kmee.com.br
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestSubsequentOperation(TransactionCase):
    def setUp(self):
        super().setUp()

        self.nfe_simples_faturamento = self.env.ref(
            "l10n_br_fiscal.demo_nfe_so_simples_faturamento"
        ).copy()

        self.so_simples_faturamento = self.env.ref(
            "l10n_br_fiscal.so_simples_faturamento"
        )

        self.tax_icms_12 = self.env.ref("l10n_br_fiscal.tax_icms_12")

        self.pis_tax_0 = self.env.ref("l10n_br_fiscal.tax_pis_0")

        self.cofins_tax_0 = self.env.ref("l10n_br_fiscal.tax_cofins_0")

    def test_subsequent_operation_simple_faturamento(self):
        """Test Fiscal Subsequent Operation Simples Faturamento"""

        self.nfe_simples_faturamento._onchange_fiscal_operation_id()
        self.nfe_simples_faturamento._onchange_company_id()
        self.nfe_simples_faturamento._onchange_document_serie_id()

        for line in self.nfe_simples_faturamento.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_fiscal_taxes()

        self.nfe_simples_faturamento.state_edoc = "a_enviar"
        self.nfe_simples_faturamento._generates_subsequent_operations()

        subsequent_documents = self.nfe_simples_faturamento.document_subsequent_ids

        for document in subsequent_documents:
            self.assertTrue(
                document.subsequent_document_id, "Subsequent document was not created"
            )

            # Subsequent Document operation
            self.assertEqual(
                document.subsequent_document_id.fiscal_operation_id.id,
                self.so_simples_faturamento.subsequent_operation_id.id,
                "Operation of the generated document is incorrect",
            )

            # Subsequent Lines
            for product in document.subsequent_document_id.fiscal_line_ids:
                # Document Line ICMS tax
                self.assertEqual(
                    product.icms_tax_id.id,
                    self.tax_icms_12.id,
                    "ICMS tax value is not 12%",
                )

                # Document Line PIS tax
                self.assertEqual(
                    product.pis_tax_id.id, self.pis_tax_0.id, "PIS tax value is not 0%"
                )

                # Document Line COFINS tax
                self.assertEqual(
                    product.cofins_tax_id.id,
                    self.cofins_tax_0.id,
                    "COFINS tax value is not 0%",
                )
