import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        return super.setup(...arguments);
    },

    // EXTENDS 'point_of_sale'
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const extraValues = super.prepareBaseLineForTaxesComputationExtraValues(customValues);
        extraValues.l10n_in_hsn_code = this.product_id?.l10n_in_hsn_code;
        return extraValues;
    },

    getL10nInReceiptComboChildLines() {
        return this.combo_line_ids
            .map((childLine) => {
                const hsnCode =
                    childLine.l10n_in_hsn_code || childLine.product_id?.l10n_in_hsn_code;
                const hsnLabel = hsnCode ? ` (${_t("HSN Code: %s", hsnCode)})` : "";
                const childLineName = `${childLine.qty} ${childLine.full_product_name}${hsnLabel}`;
                return childLine.customer_note
                    ? `${childLineName} (${_t("Note: %s", childLine.customer_note)})`
                    : childLineName;
            })
            .join(" - ");
    },
});
