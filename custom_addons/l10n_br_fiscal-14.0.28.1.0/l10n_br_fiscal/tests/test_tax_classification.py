from odoo.tests.common import Form, SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestTaxClassification(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.company = cls.env.ref("l10n_br_base.empresa_lucro_presumido")
        cls.partner = cls.env.ref("l10n_br_base.res_partner_cliente1_sp")
        cls.product = cls.env.ref("product.product_product_6")

        # Use a stable operation line already referenced in existing test suites.
        cls.operation_line = cls.env.ref("l10n_br_fiscal.fo_venda_venda")

        # Pick classifications with CBS/IBS taxes set in the provided CSV.
        cls.classification_company = cls.env.ref(
            "l10n_br_fiscal.tax_classification_000001"
        )
        cls.classification_line = cls.env.ref(
            "l10n_br_fiscal.tax_classification_200001"
        )

    def _map_kwargs(self):
        return {
            "company": self.company,
            "partner": self.partner,
            "product": self.product,
            "ncm": self.product.ncm_id,
            "nbm": self.env["l10n_br_fiscal.nbm"],
            "nbs": self.env["l10n_br_fiscal.nbs"],
            "cest": self.env["l10n_br_fiscal.cest"],
            "city_taxation_code": self.env["l10n_br_fiscal.city.taxation.code"],
            "national_taxation_code": self.env["l10n_br_fiscal.national.taxation.code"],
            "service_type": self.env["l10n_br_fiscal.service.type"],
            "ind_final": "1",
        }

    def test_map_fiscal_taxes_tax_classification_from_company(self):
        """Operation line must fallback to company tax classification when empty."""
        self.company.tax_classification_id = self.classification_company
        self.operation_line.tax_classification_id = False

        result = self.operation_line.map_fiscal_taxes(**self._map_kwargs())

        self.assertEqual(result["tax_classification"], self.classification_company)
        self.assertEqual(
            result["taxes"][self.classification_company.tax_cbs_id.tax_domain],
            self.classification_company.tax_cbs_id,
        )
        self.assertEqual(
            result["taxes"][self.classification_company.tax_ibs_id.tax_domain],
            self.classification_company.tax_ibs_id,
        )

    def test_map_fiscal_taxes_tax_classification_from_operation_line(self):
        """Operation line tax classification must override company default."""
        self.company.tax_classification_id = self.classification_company
        self.operation_line.tax_classification_id = self.classification_line

        result = self.operation_line.map_fiscal_taxes(**self._map_kwargs())

        self.assertEqual(result["tax_classification"], self.classification_line)
        self.assertEqual(
            result["taxes"][self.classification_line.tax_cbs_id.tax_domain],
            self.classification_line.tax_cbs_id,
        )
        self.assertEqual(
            result["taxes"][self.classification_line.tax_ibs_id.tax_domain],
            self.classification_line.tax_ibs_id,
        )

    def test_document_line_receives_cbs_ibs_from_tax_classification(self):
        """Fiscal document line must receive tax classification and CBS/IBS taxes."""
        self.company.tax_classification_id = self.classification_company
        self.operation_line.tax_classification_id = False

        doc_form = Form(
            self.env["l10n_br_fiscal.document"].with_context(
                default_fiscal_operation_type="out",
            )
        )
        doc_form.company_id = self.company
        doc_form.partner_id = self.partner
        doc_form.fiscal_operation_id = self.env.ref("l10n_br_fiscal.fo_venda")
        doc_form.ind_final = "1"

        with doc_form.fiscal_line_ids.new() as line_form:
            line_form.product_id = self.product
            # Ensure we map on a predictable operation line for this assertion.
            line_form.fiscal_operation_line_id = self.operation_line

            self.assertEqual(
                line_form.tax_classification_id, self.classification_company
            )
            self.assertEqual(
                line_form.cbs_tax_id, self.classification_company.tax_cbs_id
            )
            self.assertEqual(
                line_form.ibs_tax_id, self.classification_company.tax_ibs_id
            )

            self.assertIn(
                self.classification_company.tax_cbs_id, line_form.fiscal_tax_ids
            )
            self.assertIn(
                self.classification_company.tax_ibs_id, line_form.fiscal_tax_ids
            )
