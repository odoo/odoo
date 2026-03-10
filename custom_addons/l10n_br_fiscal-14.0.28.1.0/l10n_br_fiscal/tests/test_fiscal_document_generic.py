# @ 2020 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests import SavepointCase
from odoo.tests.common import Form

from ..constants.icms import ICMS_ORIGIN_TAX_IMPORTED


class TestFiscalDocumentGeneric(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Contribuinte
        cls.nfe_same_state = cls.env.ref("l10n_br_fiscal.demo_nfe_same_state")
        cls.nfe_other_state = cls.env.ref("l10n_br_fiscal.demo_nfe_other_state")
        cls.nfe_not_taxpayer = cls.env.ref("l10n_br_fiscal.demo_nfe_nao_contribuinte")

        cls.nfe_not_taxpayer_pf = cls.env.ref(
            "l10n_br_fiscal.demo_nfe_nao_contribuinte_pf"
        )

        cls.nfe_export = cls.env.ref("l10n_br_fiscal.demo_nfe_export")
        cls.company = cls.env.ref("l10n_br_base.empresa_lucro_presumido")

        # Simples Nacional
        cls.nfe_sn_same_state = cls.env.ref("l10n_br_fiscal.demo_nfe_sn_same_state")
        cls.nfe_sn_other_state = cls.env.ref("l10n_br_fiscal.demo_nfe_sn_other_state")
        cls.nfe_sn_not_taxpayer = cls.env.ref(
            "l10n_br_fiscal.demo_nfe_sn_nao_contribuinte"
        )
        cls.nfe_sn_export = cls.env.ref("l10n_br_fiscal.demo_nfe_sn_export")

        # Compra
        cls.nfe_purchase_same_state = cls.env.ref(
            "l10n_br_fiscal.demo_nfe_purchase_same_state"
        )

    def test_nfe_same_state(self):
        """Test NFe same state."""

        self.nfe_same_state._onchange_document_serie_id()
        self.nfe_same_state._onchange_fiscal_operation_id()

        for line in self.nfe_same_state.fiscal_line_ids:
            # Save the original price_unit value of the line as defined in
            # the NFe demo data.
            original_price_unit = line.price_unit

            line._onchange_product_id_fiscal()

            # Restore the original price_unit value,
            # as the product change might have altered it.
            line.price_unit = original_price_unit

            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "5102",
                    "Error to mappping CFOP 5102"
                    " for Revenda de Contribuinte Dentro do Estado.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "5101",
                    "Error to mapping CFOP 5101"
                    " for Venda de Contribuinte Dentro do Estado.",
                )

            icms_internal_sp = [
                self.env.ref("l10n_br_fiscal.tax_icms_4"),
                self.env.ref("l10n_br_fiscal.tax_icms_7"),
                self.env.ref("l10n_br_fiscal.tax_icms_12"),
                self.env.ref("l10n_br_fiscal.tax_icms_18"),
                self.env.ref("l10n_br_fiscal.tax_icms_25"),
            ]

            is_icms_internal = line.icms_tax_id in icms_internal_sp

            # ICMS
            self.assertTrue(
                is_icms_internal,
                "Error to mapping ICMS Inernal for {}"
                " for Venda de Contribuinte Dentro do "
                "Estado.".format(self.nfe_same_state.partner_id.state_id.name),
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "00",
                "Error to mapping CST 00 from ICMS 12%"
                " for Venda de Contribuinte Dentro do Estado.",
            )

            # ICMS FCP
            self.assertFalse(
                line.icmsfcp_tax_id,
                "Error to mapping ICMS FCP 2%"
                " for Venda de Contribuinte Dentro do Estado.",
            )

            # IPI
            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI NT"
                    " for Revenda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI NT"
                    " to Revenda de Contribuinte Dentro do Estado.",
                )
            else:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI 5%",
                    "Error to mapping IPI 5%"
                    " for Venda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "50",
                    "Error to mapping CST 50 from IPI 5%"
                    " to Venda de Contribuinte Dentro do Estado.",
                )

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS 0,65%",
                "Error to mapping PIS 0,65%"
                " for Venda de Contribuinte Dentro do Estado.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "01",
                "Error to mapping CST 01 - Operação Tributável com Alíquota"
                " Básica from PIS 0,65% to Venda de Contribuinte Dentro do Estado.",
            )

            # PIS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS 3%",
                "Error to mapping COFINS 3%"
                " for Venda de Contribuinte Dentro do Estado.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "01",
                "Error to mapping CST 01 - Operação Tributável com Alíquota Básica"
                " Básica to COFINS 3% de Venda de Contribuinte Dentro do Estado.",
            )

            product_total = line.price_unit * line.quantity
            self.assertEqual(line.price_gross, product_total)

        self.nfe_same_state.action_document_confirm()

        # Total value of the products
        self.assertEqual(self.nfe_same_state.amount_price_gross, 200)

    def test_nfe_other_state(self):
        """Test NFe other state."""

        self.nfe_other_state._onchange_document_serie_id()
        self.nfe_other_state._onchange_fiscal_operation_id()

        for line in self.nfe_other_state.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "6102",
                    "Error to mapping CFOP 6102"
                    " for Revenda de Contribuinte p/ Fora do Estado.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "6101",
                    "Error to mapping CFOP 6101"
                    " for Venda de Contribuinte p/ Fora do Estado.",
                )

            # ICMS
            if line.product_id.icms_origin in ICMS_ORIGIN_TAX_IMPORTED:
                self.assertEqual(
                    line.icms_tax_id.name,
                    "ICMS 4%",
                    "Error to mapping ICMS 4%"
                    " for Venda de Contribuinte p/ Fora do Estado.",
                )
                self.assertEqual(
                    line.icms_cst_id.code,
                    "00",
                    "Error to mapping CST 00 from ICMS 4%"
                    " for Venda de Contribuinte p/ Fora do Estado.",
                )
            else:
                self.assertEqual(
                    line.icms_tax_id.name,
                    "ICMS 7%",
                    "Error to mapping ICMS 7%"
                    " for Venda de Contribuinte p/ Fora do Estado.",
                )
                self.assertEqual(
                    line.icms_cst_id.code,
                    "00",
                    "Error to mapping CST 00 from ICMS 7%"
                    " for Venda de Contribuinte p/ Fora do Estado.",
                )

            # ICMS FCP
            self.assertFalse(
                line.icmsfcp_tax_id,
                "Error to mapping ICMS FCP 2%"
                " for Venda de Contribuinte Dentro do Estado.",
            )

            # IPI
            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI NT"
                    " for Revenda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI NT"
                    " to Revenda de Contribuinte Dentro do Estado.",
                )
            else:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI 5%",
                    "Error to mapping IPI 5%"
                    " for Venda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "50",
                    "Error to mapping CST 50 from IPI 5%"
                    " to Venda de Contribuinte Dentro do Estado.",
                )

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS 0,65%",
                "Error to mapping PIS 0,65%"
                " for Venda de Contribuinte p/ Fora do Estado.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "01",
                "Error to mapping CST 01 - Operação Tributável com Alíquota"
                " Básica from PIS 0,65% for"
                " Venda de Contribuinte p/ Fora do Estado.",
            )

            # PIS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS 3%",
                "Error to mapping COFINS 3%"
                " for Venda de Contribuinte p/ Fora do Estado.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "01",
                "Error to mapping CST 01 -"
                " Operação Tributável com Alíquota Básica"
                "from COFINS 3% for Venda de Contribuinte p/ Fora do Estado.",
            )

    def test_nfe_not_taxpayer(self):
        """Test NFe not taxpayer."""

        self.nfe_not_taxpayer._onchange_document_serie_id()
        self.nfe_not_taxpayer._onchange_fiscal_operation_id()

        for line in self.nfe_not_taxpayer.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "6108",
                    "Error to mapping CFOP 6108"
                    " for Revenda de Contribuinte p/ Não Contribuinte.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "6107",
                    "Error to mapping CFOP 6107"
                    " for Venda de Contribuinte p/ Não Contribuinte.",
                )

            # ICMS
            self.assertEqual(
                line.icms_tax_id.name,
                "ICMS 12%",
                "Error to mapping ICMS 12%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "00",
                "Error to mapping CST 00 from ICMS 12%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )

            # ICMS FCP
            self.assertEqual(
                line.icmsfcp_tax_id.name,
                "FCP 2%",
                "Erro ao mapear ICMS FCP 2%"
                " para Venda de Contribuinte p/ Não Contribuinte.",
            )

            # IPI
            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI NT"
                    " for Revenda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI NT"
                    " to Revenda de Contribuinte Dentro do Estado.",
                )
            else:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI 5%",
                    "Error to mapping IPI 5%"
                    " for Venda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "50",
                    "Error to mapping CST 50 from IPI 5%"
                    " to Venda de Contribuinte Dentro do Estado.",
                )

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS 0,65%",
                "Error to mapping PIS 0,65%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "01",
                "Error to mapping CST 01 - Operação Tributável com Alíquota"
                " Básica from PIS 0,65% for"
                " Venda de Contribuinte p/ Não Contribuinte.",
            )

            # PIS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS 3%",
                "Error to mapping COFINS 3%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "01",
                "Error to mapping CST 01 -"
                " Operação Tributável com Alíquota Básica"
                "from COFINS 3% for Venda de Contribuinte p/ Não Contribuinte.",
            )

    def test_nfe_not_taxpayer_not_company(self):
        """Test NFe not taxpayer not Company."""

        self.nfe_not_taxpayer_pf._onchange_document_serie_id()
        self.nfe_not_taxpayer_pf._onchange_fiscal_operation_id()

        for line in self.nfe_not_taxpayer_pf.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "6108",
                    "Error to mapping CFOP 6108"
                    " for Revenda de Contribuinte p/ Não Contribuinte.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "6107",
                    "Error to mapping CFOP 6107"
                    " for Venda de Contribuinte p/ Não Contribuinte.",
                )

            # ICMS
            self.assertEqual(
                line.icms_tax_id.name,
                "ICMS 12%",
                "Error to mapping ICMS 12%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "00",
                "Error to mapping CST 00 from ICMS 12%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )

            # ICMS FCP
            self.assertEqual(
                line.icmsfcp_tax_id.name,
                "FCP 2%",
                "Erro ao mapear ICMS FCP 2%"
                " para Venda de Contribuinte p/ Não Contribuinte.",
            )

            # IPI
            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI NT"
                    " for Revenda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI NT"
                    " to Revenda de Contribuinte Dentro do Estado.",
                )
            else:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI 5%",
                    "Error to mapping IPI 5%"
                    " for Venda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "50",
                    "Error to mapping CST 50 from IPI 5%"
                    " to Venda de Contribuinte Dentro do Estado.",
                )

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS 0,65%",
                "Error to mapping PIS 0,65%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "01",
                "Error to mapping CST 01 - Operação Tributável com Alíquota"
                " Básica from PIS 0,65% for"
                " Venda de Contribuinte p/ Não Contribuinte.",
            )

            # PIS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS 3%",
                "Error to mapping COFINS 3%"
                " for Venda de Contribuinte p/ Não Contribuinte.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "01",
                "Error to mapping CST 01 -"
                " Operação Tributável com Alíquota Básica"
                "from COFINS 3% for Venda de Contribuinte p/ Não Contribuinte.",
            )

    def test_nfe_export(self):
        """Test NFe export."""

        self.nfe_export._onchange_document_serie_id()
        self.nfe_export._onchange_fiscal_operation_id()

        for line in self.nfe_export.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "7102",
                    "Error to mapping CFOP 7102"
                    " for Revenda de Contribuinte p/ o Exterior.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "7101",
                    "Error to mapping CFOP 7101"
                    " for Venda de Contribuinte p/ o Exterior.",
                )

            # ICMS - TODO field missing
            # self.assertEqual(
            #    line.icms_tax_id.name, 'ICMS 7%',
            #    "Error to mapping ICMS 7%"
            #    " for Venda de Contribuinte p/ o Exterior.")
            # self.assertEqual(
            #    line.icms_cst_id.code, '00',
            #    "Error to mapping CST 00 from ICMS 7%"
            #    " for Venda de Contribuinte p/ o Exterior.")

            # ICMS FCP
            # self.assertEqual(
            #    line.icmsfcp_tax_id.name, 'FCP 2%',
            #    "Erro ao mapear ICMS FCP 2%"
            #    " para Venda de Contribuinte p/ o Exterior.")

            # IPI
            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI NT"
                    " for Revenda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI NT"
                    " to Revenda de Contribuinte Dentro do Estado.",
                )
            else:
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI 5%",
                    "Error to mapping IPI 5%"
                    " for Venda de Contribuinte Dentro do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "50",
                    "Error to mapping CST 50 from IPI 5%"
                    " to Venda de Contribuinte Dentro do Estado.",
                )

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS 0,65%",
                "Error to mapping PIS 0,65%"
                " for Venda de Contribuinte p/ o Exterior.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "01",
                "Error to mapping CST 01 - Operação Tributável com Alíquota"
                " Básica from PIS 0,65% for"
                " Venda de Contribuinte p/ o Exterior.",
            )

            # PIS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS 3%",
                "Error to mapping COFINS 3%"
                " for Venda de Contribuinte p/ o Exterior.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "01",
                "Error to mapping CST 01 -"
                " Operação Tributável com Alíquota Básica"
                "from COFINS 3% for Venda de Contribuinte p/ o Exterior.",
            )

    def test_nfe_sn_same_state(self):
        """Test NFe Simples Nacional same state."""

        self.nfe_sn_same_state._onchange_document_serie_id()
        self.nfe_sn_same_state._onchange_fiscal_operation_id()

        for line in self.nfe_sn_same_state.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()

            # set fake estimate tax
            line.ncm_id.tax_estimate_ids.create(
                {
                    "ncm_id": line.ncm_id.id,
                    "state_id": line.company_id.state_id.id,
                    "key": "fake estimate tax",
                    "origin": "fake estimate tax",
                    "federal_taxes_national": 33.00,
                }
            )

            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "5102",
                    "Error to mappping CFOP 5102"
                    " for Revenda de Simples Nacional Dentro do Estado.",
                )
                # IPI
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "5101",
                    "Error to mapping CFOP 5101"
                    " for Venda de Simples Nacional Dentro do Estado.",
                )
                # IPI
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI Outros",
                    "Error to mapping IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "99",
                    "Error to mapping CST 99 from IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )

            # ICMS
            self.assertEqual(
                line.icmssn_tax_id.name,
                "ICMS SN Com Permissão de Crédito",
                "Error to mapping ICMS SN Com Permissão de Crédito"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "101",
                "Error to mapping CST 101 do ICMS SN Com Permissão de Crédito"
                " for Venda de Simples Nacional Dentro do Estado.",
            )

            # ICMS FCP - TODO mapping failed
            # self.assertEqual(
            #    line.icmsfcp_tax_id.name, 'FCP 2%',
            #    "Erro ao mapear ICMS FCP 2%"
            #    " para Venda de Simples Nacional Dentro do Estado.")

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS Outros",
                "Error to mapping PIS Simples Nacional"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "49",
                "Error to mapping CST 49 Outras Operações de Saída"
                " from PIS Simples Nacional from Venda de"
                " Simples Nacional Dentro do Estado.",
            )

            # COFINS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS Outros",
                "Error to mapping COFINS Simples Nacional"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "49",
                "Error to mapping CST 49 Outras Operações de Saída"
                " from COFINS Simples Nacional for Venda de"
                " Simples Nacional Fora do Estado.",
            )

        # ESTIMATE TAXES
        self.assertEqual(self.nfe_sn_same_state.amount_estimate_tax, 1308.45)

    def test_nfe_sn_other_state(self):
        """Test NFe SN other state."""

        self.nfe_sn_other_state._onchange_document_serie_id()
        self.nfe_sn_other_state._onchange_fiscal_operation_id()

        for line in self.nfe_sn_other_state.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "6102",
                    "Error to mappping CFOP 6102"
                    " for Revenda de Simples Nacional Fora do Estado.",
                )
                # IPI
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "6101",
                    "Error to mapping CFOP 6101"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                # IPI
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI Outros",
                    "Error to mapping IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "99",
                    "Error to mapping CST 99 from IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )

            # ICMS
            self.assertEqual(
                line.icmssn_tax_id.name,
                "ICMS SN Com Permissão de Crédito",
                "Error to mapping ICMS SN Com Permissão de Crédito"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "101",
                "Erro ao mapear a CST 101 do ICMS SN Com Permissão de Crédito"
                " para Venda de Simples Nacional Dentro do Estado.",
            )

            # ICMS FCP - TODO mapping failed
            # self.assertEqual(
            #    line.icmsfcp_tax_id.name, 'FCP 2%',
            #    "Erro ao mapear ICMS FCP 2%"
            #    " para Venda de Simples Nacional Fora do Estado.")

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS Outros",
                "Erro ao mapear PIS Simples Nacional"
                " para Venda de Simples Nacional Fora do Estado.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "49",
                "Erro ao mapear a CST 49 Outras Operações de Saída"
                " com Alíquota Básica do PIS Simples Nacional de Venda de"
                " Simples Nacional Dentro do Estado.",
            )

            # COFINS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS Outros",
                "Error to mapping COFINS Simples Nacional"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "49",
                "Error to mapping CST 49 Outras Operações de Saída"
                " from COFINS Simples Nacional for Venda de"
                " Simples Nacional Fora do Estado.",
            )

    def test_nfe_sn_not_taxpayer(self):
        """Test NFe SN not taxpayer."""

        self.nfe_sn_not_taxpayer._onchange_document_serie_id()
        self.nfe_sn_not_taxpayer._onchange_fiscal_operation_id()

        for line in self.nfe_sn_not_taxpayer.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "5102",
                    "Error to mappping CFOP 5102"
                    " for Revenda de Simples Nacional Fora do Estado.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "5101",
                    "Error to mapping CFOP 5101"
                    " for Venda de Simples Nacional Fora do Estado.",
                )

            # ICMS
            self.assertEqual(
                line.icms_tax_id.name,
                "ICMS 18%",
                "Error to mapping ICMS 18%"
                " for Venda de Simples Nacional Fora do Estado.",
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "00",
                "Erro ao mapear a CST 00 do ICMS 18%"
                " para Venda de Simples Nacional Fora do Estado.",
            )

            # ICMS FCP
            # self.assertEqual(
            #     line.icmsfcp_tax_id.name, 'FCP 2%',
            #     "Erro ao mapear ICMS FCP 2%"
            #     " para Venda de Simples Nacional Fora do Estado.")

            # IPI
            self.assertEqual(
                line.ipi_tax_id.name,
                "IPI 5%",
                "Erro ao mapear IPI 5%"
                " para Venda de Simples Nacional Fora do Estado.",
            )
            self.assertEqual(
                line.ipi_cst_id.code,
                "50",
                "Erro ao mapear a CST 50 do IPI 5%"
                " de Venda de Simples Nacional Fora do Estado.",
            )

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS 0,65%",
                "Erro ao mapear PIS 0,65%"
                " para Venda de Simples Nacional Fora do Estado.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "01",
                "Erro ao mapear a CST 01 - Operação Tributável"
                " com Alíquota Básica do PIS 0,65% de Venda de"
                " Simples Nacional Fora do Estado.",
            )

            # PIS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS 3%",
                "Erro ao mapear COFINS 3%"
                " para Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "01",
                "Erro ao mapear a CST 01 - Operação Tributável"
                " com Alíquota Básica do COFINS 3% de Venda de"
                " Simples Nacional Fora do Estado.",
            )

    def test_nfe_sn_export(self):
        """Test NFe SN export."""

        self.nfe_sn_export._onchange_document_serie_id()
        self.nfe_sn_export._onchange_fiscal_operation_id()

        for line in self.nfe_sn_export.fiscal_line_ids:
            line._onchange_product_id_fiscal()
            line._onchange_commercial_quantity()
            line._onchange_fiscal_operation_id()
            line._onchange_fiscal_operation_line_id()
            line._onchange_fiscal_taxes()

            if "Revenda" in line.fiscal_operation_line_id.name:
                self.assertEqual(
                    line.cfop_id.code,
                    "7102",
                    "Error to mapping CFOP 7102"
                    " for Revenda de Contribuinte p/ o Exterior.",
                )
                # IPI
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI NT",
                    "Error to mapping IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "53",
                    "Error to mapping CST 53 from IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
            else:
                self.assertEqual(
                    line.cfop_id.code,
                    "7101",
                    "Error to mapping CFOP 7101"
                    " for Venda de Contribuinte p/ o Exterior.",
                )
                # IPI
                self.assertEqual(
                    line.ipi_tax_id.name,
                    "IPI Outros",
                    "Error to mapping IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )
                self.assertEqual(
                    line.ipi_cst_id.code,
                    "99",
                    "Error to mapping CST 99 from IPI Simples Nacional"
                    " for Venda de Simples Nacional Fora do Estado.",
                )

            # ICMS
            self.assertEqual(
                line.icmssn_tax_id.name,
                "ICMS SN Com Permissão de Crédito",
                "Error to mapping ICMS SN Com Permissão de Crédito"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.icms_cst_id.code,
                "101",
                "Erro ao mapear a CST 101 do ICMS SN Com Permissão de Crédito"
                " para Venda de Simples Nacional Dentro do Estado.",
            )

            # ICMS FCP
            # self.assertEqual(
            #    line.icmsfcp_tax_id.name, 'FCP 2%',
            #    "Erro ao mapear ICMS FCP 2%"
            #    " para Venda de Contribuinte p/ o Exterior.")

            # PIS
            self.assertEqual(
                line.pis_tax_id.name,
                "PIS Outros",
                "Erro ao mapear PIS Simples Nacional"
                " para Venda de Simples Nacional Fora do Estado.",
            )
            self.assertEqual(
                line.pis_cst_id.code,
                "49",
                "Erro ao mapear a CST 49 Outras Operações de Saída"
                " com Alíquota Básica do PIS Simples Nacional de Venda de"
                " Simples Nacional Dentro do Estado.",
            )

            # COFINS
            self.assertEqual(
                line.cofins_tax_id.name,
                "COFINS Outros",
                "Error to mapping COFINS Simples Nacional"
                " for Venda de Simples Nacional Dentro do Estado.",
            )
            self.assertEqual(
                line.cofins_cst_id.code,
                "49",
                "Error to mapping CST 49 Outras Operações de Saída"
                " from COFINS Simples Nacional for Venda de"
                " Simples Nacional Fora do Estado.",
            )

    def test_nfe_return(self):
        """Test Fiscal Document Return"""
        action = self.nfe_same_state.action_create_return()
        return_id = self.nfe_same_state.browse(
            [i[2][0] for i in action["domain"] if i[0] == "id"]
        )

        self.assertEqual(
            return_id.fiscal_operation_id.id,
            self.nfe_same_state.fiscal_operation_id.return_fiscal_operation_id.id,
            "Error on creation return",
        )

    def test_difal_calculation(self):
        partner = self.env.ref("l10n_br_base.res_partner_cliente5_pe")
        partner.ind_ie_dest = "9"
        doc_form = Form(
            self.env["l10n_br_fiscal.document"].with_context(
                default_fiscal_operation_type="out",
            )
        )
        doc_form.company_id = self.company
        doc_form.partner_id = partner
        doc_form.fiscal_operation_id = self.env.ref("l10n_br_fiscal.fo_venda")

        product = self.env.ref("product.product_product_6")
        with doc_form.fiscal_line_ids.new() as line_form:
            line_form.product_id = product
            line_form.price_unit = 100.0
            line_form.quantity = 1.0

        doc = doc_form.save()
        line = doc.fiscal_line_ids[0]
        self.assertEqual(line.icms_destination_base, 100.0)
        self.assertEqual(line.icms_origin_percent, 7.0)
        self.assertEqual(line.icms_destination_percent, 20.5)
        self.assertEqual(line.icms_destination_value, 13.5)

    def test_nfe_comments(self):
        self.nfe_not_taxpayer._document_comment()
        additional_data = self.nfe_not_taxpayer.fiscal_line_ids[0].additional_data
        self.assertEqual(
            additional_data,
            "manual comment test - Valor Aprox. dos Tributos: R$ 0,00",
            # TODO FIXME changed 0.00 to 0,00 to get tests pass on v13, but not
            # correct
        )

    def test_fields_freight_insurance_other_costs(self):
        """Test fields Freight, Insurance and Other Costs when
        defined or By Line or By Total.
        """

        # Teste definindo os valores Por Linha
        for line in self.nfe_same_state.fiscal_line_ids:
            line.freight_value = 10.0
            line.insurance_value = 10.0
            line.other_value = 10.0

        self.assertEqual(
            self.nfe_same_state.amount_freight_value,
            20.0,
            "Unexpected value for the field" " Amount Freight in Fiscal Document line",
        )
        self.assertEqual(
            self.nfe_same_state.amount_insurance_value,
            20.0,
            "Unexpected value for the field"
            " Amount Insurance in Fiscal Document line",
        )
        self.assertEqual(
            self.nfe_same_state.amount_other_value,
            20.0,
            "Unexpected value for the field"
            " Amount Other Value in Fiscal Document line",
        )

        # Teste definindo os valores Por Total
        # Por padrão a definição dos campos está por Linha
        self.nfe_same_state.company_id.delivery_costs = "total"

        # Caso que os Campos na Linha tem valor
        self.nfe_same_state.amount_freight_value = 10.0
        self.nfe_same_state.amount_insurance_value = 10.0
        self.nfe_same_state.amount_other_value = 10.0

        for line in self.nfe_same_state.fiscal_line_ids:
            self.assertEqual(
                line.freight_value,
                5.0,
                "Unexpected value for the field" " Freight in Fiscal Document line",
            )
            self.assertEqual(
                line.insurance_value,
                5.0,
                "Unexpected value for the field" " Insurance in Fiscal Document line",
            )
            self.assertEqual(
                line.other_value,
                5.0,
                "Unexpected value for the field"
                " Other Values in Fiscal Document line",
            )

        # Caso que os Campos na Linha não tem valor
        for line in self.nfe_same_state.fiscal_line_ids:
            line.freight_value = 0.0
            line.insurance_value = 0.0
            line.other_value = 0.0

        self.nfe_same_state.amount_freight_value = 20.0
        self.nfe_same_state.amount_insurance_value = 20.0
        self.nfe_same_state.amount_other_value = 20.0

        for line in self.nfe_same_state.fiscal_line_ids:
            self.assertEqual(
                line.freight_value,
                10.0,
                "Unexpected value for the field" " Freight in Fiscal Document line",
            )
            self.assertEqual(
                line.insurance_value,
                10.0,
                "Unexpected value for the field" " Insurance in Fiscal Document line",
            )
            self.assertEqual(
                line.other_value,
                10.0,
                "Unexpected value for the field"
                " Other Values in Fiscal Document line",
            )
