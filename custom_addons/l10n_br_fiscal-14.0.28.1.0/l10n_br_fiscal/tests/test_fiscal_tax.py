# Copyright 2020 Akretion - Renato Lima <renato.lima@akretion.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import SavepointCase
from odoo.tools import float_compare

from ..constants.fiscal import FINAL_CUSTOMER_NO, FINAL_CUSTOMER_YES
from ..constants.icms import ICMS_ORIGIN_DEFAULT


class TestFiscalTax(SavepointCase):
    def _check_compute_taxes_result(self, test_result, compute_result, currency):
        for tax_domain in test_result["taxes"]:
            for tax_field in test_result["taxes"][tax_domain]:
                self.assertEqual(
                    float_compare(
                        test_result["taxes"][tax_domain][tax_field],
                        compute_result["taxes"][tax_domain][tax_field],
                        precision_rounding=currency.rounding,
                    ),
                    0,
                    "{} {} {} {}".format(
                        tax_domain,
                        tax_field,
                        test_result["taxes"][tax_domain][tax_field],
                        compute_result["taxes"][tax_domain][tax_field],
                    ),
                )

        self.assertEqual(
            float_compare(
                compute_result["amount_included"],
                test_result["amount_included"],
                precision_rounding=currency.rounding,
            ),
            0,
            f"Amount included diff: "
            f"{compute_result['amount_included']} - "
            f"{test_result['amount_included']}.",
        )
        self.assertEqual(
            float_compare(
                compute_result["amount_not_included"],
                test_result["amount_not_included"],
                precision_rounding=currency.rounding,
            ),
            0,
            f"Amount not included diff: "
            f"{compute_result['amount_not_included']} - "
            f"{test_result['amount_not_included']}.",
        )
        self.assertEqual(
            float_compare(
                compute_result["amount_withholding"],
                test_result["amount_withholding"],
                precision_rounding=currency.rounding,
            ),
            0,
            f"Amount Withholding diff: "
            f"{compute_result['amount_withholding']} - "
            f"{test_result['amount_withholding']}.",
        )
        self.assertEqual(
            float_compare(
                compute_result["estimate_tax"],
                test_result["estimate_tax"],
                precision_rounding=currency.rounding,
            ),
            0,
            f"Estimate Tax diff: "
            f"{compute_result['estimate_tax']} - "
            f"{test_result['estimate_tax']}.",
        )

    def _create_compute_taxes_kwargs(self):
        return {
            "company": self.env.ref("l10n_br_base.empresa_lucro_presumido"),
            "partner": self.env.ref("l10n_br_base.res_partner_cliente5_pe"),
            "product": self.env.ref("product.product_product_12"),
            "price_unit": 3.143539,
            "quantity": 11.000,
            "uom_id": self.env.ref("uom.product_uom_unit"),
            "fiscal_price": 3.143539,
            "fiscal_quantity": 11.000,
            "uot_id": self.env.ref("uom.product_uom_unit"),
            "discount_value": 0.00,
            "insurance_value": 0.00,
            "other_value": 0.00,
            "freight_value": 0.00,
            "ii_customhouse_charges": 0.00,
            "ii_iof_value": 0.00,
            "ncm": self.env.ref("l10n_br_fiscal.ncm_72132000"),
            "nbs": False,
            "nbm": False,
            "cest": False,
            "operation_line": self.env.ref("l10n_br_fiscal.fo_venda_venda"),
            "cfop": self.env.ref("l10n_br_fiscal.cfop_6101"),
            "icmssn_range": False,
            "icms_origin": ICMS_ORIGIN_DEFAULT,
            "ind_final": FINAL_CUSTOMER_YES,
        }

    def test_compute_taxes_01(self):
        """Testa o calculo dos impostos venda para pessoa física"""

        kwargs = self._create_compute_taxes_kwargs()
        currency = kwargs["company"].currency_id

        fiscal_taxes = self.env["l10n_br_fiscal.tax"]
        fiscal_taxes |= (
            self.env.ref("l10n_br_fiscal.tax_icms_7")
            + self.env.ref("l10n_br_fiscal.tax_ipi_15")
            + self.env.ref("l10n_br_fiscal.tax_pis_0_65")
            + self.env.ref("l10n_br_fiscal.tax_cofins_3")
        )

        compute_result = fiscal_taxes.compute_taxes(**kwargs)

        test_result = {
            "amount_included": 4.04,
            "amount_not_included": 5.19,
            "amount_withholding": 0.0,
            "estimate_tax": 0.0,
            "taxes": {
                "ipi": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 15.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 5.19,
                },
                "icms": {
                    "base": 39.77,
                    "base_reduction": 0.0,
                    "percent_amount": 7.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 2.78,
                    "add_to_base": 5.19,
                },
                "pis": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 0.65,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 0.22,
                },
                "cofins": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 3.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 1.04,
                },
            },
        }

        self._check_compute_taxes_result(test_result, compute_result, currency)

    def test_compute_taxes_02(self):
        """Testa o calculo dos impostos venda para pessoa física"""

        kwargs = self._create_compute_taxes_kwargs()
        currency = kwargs["company"].currency_id
        kwargs["ind_final"] = FINAL_CUSTOMER_NO

        fiscal_taxes = self.env["l10n_br_fiscal.tax"]
        fiscal_taxes |= (
            self.env.ref("l10n_br_fiscal.tax_icms_7")
            + self.env.ref("l10n_br_fiscal.tax_ipi_15")
            + self.env.ref("l10n_br_fiscal.tax_pis_0_65")
            + self.env.ref("l10n_br_fiscal.tax_cofins_3")
        )

        compute_result = fiscal_taxes.compute_taxes(**kwargs)

        test_result = {
            "amount_included": 3.68,
            "amount_not_included": 5.19,
            "amount_withholding": 0.0,
            "estimate_tax": 0.0,
            "taxes": {
                "ipi": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 15.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 5.19,
                },
                "icms": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 7.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 2.42,
                    "add_to_base": 0.0,
                },
                "pis": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 0.65,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 0.22,
                },
                "cofins": {
                    "base": 34.58,
                    "base_reduction": 0.0,
                    "percent_amount": 3.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 1.04,
                },
            },
        }

        self._check_compute_taxes_result(test_result, compute_result, currency)

    def test_compute_taxes_03(self):
        """Testa o calculo dos impostos de compra - entrada de importação"""

        kwargs = self._create_compute_taxes_kwargs()
        currency = kwargs["company"].currency_id

        kwargs["partner"] = self.env.ref("base.res_partner_12")
        kwargs["price_unit"] = 49.63180
        kwargs["quantity"] = 5.00
        kwargs["fiscal_price"] = 49.63180
        kwargs["fiscal_quantity"] = 5.00
        kwargs["insurance_value"] = 0.00
        kwargs["other_value"] = 74.87
        kwargs["freight_value"] = 0.00
        kwargs["ii_customhouse_charges"] = 7.72
        kwargs["ii_iof_value"] = 0.00
        kwargs["operation_line"] = self.env.ref("l10n_br_fiscal.fo_compras_compras")
        kwargs["cfop"] = self.env.ref("l10n_br_fiscal.cfop_3101")

        fiscal_taxes = self.env["l10n_br_fiscal.tax"]
        fiscal_taxes |= (
            self.env.ref("l10n_br_fiscal.tax_icms_17")
            + self.env.ref("l10n_br_fiscal.tax_ii_10")
            + self.env.ref("l10n_br_fiscal.tax_ipi_15")
            + self.env.ref("l10n_br_fiscal.tax_pis_monofasico_2_10")
            + self.env.ref("l10n_br_fiscal.tax_cofins_monofasico_10_68")
        )

        compute_result = fiscal_taxes.compute_taxes(**kwargs)

        test_result = {
            "amount_included": 142.74,
            "amount_not_included": 52.18,
            "amount_withholding": 0.0,
            "estimate_tax": 0.0,
            "taxes": {
                "ii": {
                    "base": 248.16,
                    "base_reduction": 0.0,
                    "percent_amount": 10.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 24.82,
                },
                "ipi": {
                    "base": 347.85,
                    "base_reduction": 0.0,
                    "percent_amount": 15.0,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 52.18,
                },
                "icms": {
                    "base": 450.8,
                    "base_reduction": 0.0,
                    "percent_amount": 17.00,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 76.64,
                    "add_to_base": 200.87,
                    "remove_from_base": 74.87,
                },
                "pis": {
                    "base": 323.03,
                    "base_reduction": 0.0,
                    "percent_amount": 2.10,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 6.78,
                },
                "cofins": {
                    "base": 323.03,
                    "base_reduction": 0.0,
                    "percent_amount": 10.68,
                    "percent_reduction": 0.0,
                    "value_amount": 0.0,
                    "tax_value": 34.5,
                },
            },
        }

        self._check_compute_taxes_result(test_result, compute_result, currency)
