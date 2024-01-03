/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";

patch(PosOrder.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.get_partner()) {
            result.partner = this.get_partner();
        }
        if (this.company.country_id?.code === "IN") {
            result.l10n_in_hsn_summary = this._prepareL10nInHsnSummary();
            result.tax_details.forEach((tax) => {
                if (tax?._l10n_in_tax_type) {
                    tax._letter = tax._l10n_in_tax_type.toUpperCase();
                }
            });
        }
        return result;
    },
    _prepareL10nInHsnSummary() {
        const hsnSummary = {};
        const accountTagByXmlRefId = this.pos.account_tag_by_xml_ref_id;
        const fiscalPosition = this.fiscal_position_id;
        this.orderlines.forEach((line) => {
            const hsnCode = line.get_product()?.l10n_in_hsn_code;
            const taxes_ids = line.tax_ids || line.product.taxes_id;
            if (hsnCode && taxes_ids) {
                const product_taxes = line.pos.get_taxes_after_fp(taxes_ids, fiscalPosition);
                const price_unit = line.get_unit_price();
                const quantity = line.get_quantity();
                const all_taxes = line.compute_all(
                    product_taxes,
                    price_unit,
                    quantity,
                    line.pos.currency.rounding
                );
                //It is require to pre-compute GST Rate as we may have same hsn with different gst rates
                const gstRate = formatFloat(this._computeL10nInGSTRate(all_taxes.taxes), {
                    decimals: 2,
                    trailingZeros: false,
                });
                const groupKey = "".concat(hsnCode, "-", gstRate);
                if (!hsnSummary[groupKey]) {
                    hsnSummary[groupKey] = {
                        l10n_in_hsn_code: hsnCode,
                        gst_rate: gstRate,
                        SGST: { rate: 0, amount: 0 },
                        CGST: { rate: 0, amount: 0 },
                        IGST: { rate: 0, amount: 0 },
                        CESS: { amount: 0 },
                    };
                }
                const l10nInTaxKeyByTagRef = this._getl10nInTaxKeyByTagRef();
                all_taxes.taxes.forEach((tax) => {
                    tax.repartition_line_ids.forEach((line) => {
                        line.tag_ids.forEach((tag) => {
                            const tagRef = accountTagByXmlRefId[tag.id];
                            const factor_percent = line.factor_percent;
                            const taxKey = l10nInTaxKeyByTagRef[tagRef];
                            switch (taxKey) {
                                case "CGST":
                                case "SGST":
                                case "IGST":
                                    hsnSummary[groupKey][taxKey]["amount"] +=
                                        (factor_percent * tax.amount) / 100;
                                    hsnSummary[groupKey][taxKey]["rate"] =
                                        (factor_percent * tax.tax_rate) / 100;
                                    break;
                                case "CESS":
                                    hsnSummary[groupKey][taxKey]["amount"] +=
                                        (factor_percent * tax.amount) / 100;
                                    break;
                            }
                        });
                    });
                });
            }
        });
        const hsnSummaryLines = Object.keys(hsnSummary);
        const showSymbol = true;
        hsnSummaryLines.forEach((line) => {
            const line_value = hsnSummary[line];
            line_value.CGST.amount = this.env.utils.formatCurrency(
                line_value.CGST.amount,
                showSymbol
            );
            line_value.SGST.amount = this.env.utils.formatCurrency(
                line_value.SGST.amount,
                showSymbol
            );
            line_value.IGST.amount = this.env.utils.formatCurrency(
                line_value.IGST.amount,
                showSymbol
            );
            line_value.CESS.amount = this.env.utils.formatCurrency(
                line_value.CESS.amount,
                showSymbol
            );
        });
        return hsnSummaryLines.length ? hsnSummary : null;
    },
});
