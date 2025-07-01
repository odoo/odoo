import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { lt } from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.company.country_id?.code === "IN") {
            result.l10n_in_hsn_summary = this._prepareL10nInHsnSummary();
        }
        return result;
    },
    _prepareL10nInHsnSummary() {
        const currency = this.config.currency_id;
        const company = this.company;
        const orderLines = this.lines;

        // If each line is negative, we assume it's a refund order.
        // It's a normal order if it doesn't contain a line (useful for pos_settle_due).
        // TODO: Properly differentiate refund orders from normal ones.
        const documentSign =
            this.lines.length === 0 ||
            !this.lines.every((l) => lt(l.qty, 0, { decimals: currency.decimal_places }))
                ? 1
                : -1;

        const baseLines = orderLines.map((line) => {
            return accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues({
                    quantity: documentSign * line.qty,
                })
            );
        });
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);
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
