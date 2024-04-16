/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import {
    getTaxesAfterFiscalPosition,
    getTaxesValues,
} from "@point_of_sale/app/models/utils/tax_utils";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
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
        const fiscalPosition = this.fiscal_position_id;
        const baseLines = [];
        this.orderlines.forEach((line) => {
            const hsnCode = line.get_product()?.l10n_in_hsn_code;
            if (!hsnCode) {
                return;
            }

            let taxes = line.tax_ids || line.product.taxes_id;
            if (fiscalPosition) {
                taxes = getTaxesAfterFiscalPosition(taxes, this.fiscal_position_id, this.models);
            }

            const priceUnit = line.get_unit_price();
            baseLines.push({
                l10n_in_hsn_code: hsnCode,
                price_unit: priceUnit,
                quantity: line.get_quantity(),
                uom: null,
                taxes_data: getTaxesValues(
                    taxes,
                    priceUnit,
                    1,
                    line.product,
                    this.company,
                    this.currency
                ),
            });
        });

        const hsnSummary = accountTaxHelpers.l10n_in_get_hsn_summary_table(baseLines, false);
        if (hsnSummary) {
            for (const item of hsnSummary.items) {
                for (const key of [
                    "tax_amount_igst",
                    "tax_amount_cgst",
                    "tax_amount_sgst",
                    "tax_amount_cess",
                ]) {
                    item[key] = formatCurrency(item[key], this.currency);
                }
            }
        }
        return hsnSummary;
    },
});
