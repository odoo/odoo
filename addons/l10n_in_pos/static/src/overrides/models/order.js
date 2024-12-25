/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.company.country_id?.code === "IN") {
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
        const fiscalPosition = this.fiscal_position;
        const baseLines = [];
        this.orderlines.forEach((line) => {
            const hsnCode = line.get_product()?.l10n_in_hsn_code;
            if (!hsnCode) {
                return;
            }

            let taxes = line.tax_ids || line.product.taxes_id;
            if (fiscalPosition) {
                taxes = this.pos.getTaxesAfterFiscalPosition(taxes, fiscalPosition);
            }

            baseLines.push({
                l10n_in_hsn_code: hsnCode,
                price_unit: line.get_unit_price(),
                quantity: line.get_quantity(),
                discount: line.get_discount(),
                uom: null,
                taxes_data: this.pos.mapTaxValues(taxes),
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
                    item[key] = this.env.utils.formatCurrency(item[key], true);
                }
            }
        }
        return hsnSummary;
    },
});
