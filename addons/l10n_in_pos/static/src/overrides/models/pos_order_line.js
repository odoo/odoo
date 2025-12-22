import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        this.l10n_in_hsn_code = this.product_id.l10n_in_hsn_code || "";
        return super.setup(...arguments);
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            l10n_in_hsn_code: this.get_product().l10n_in_hsn_code || "",
        };
    },

    // EXTENDS 'point_of_sale'
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const extraValues = super.prepareBaseLineForTaxesComputationExtraValues(customValues);
        extraValues.l10n_in_hsn_code = this.product_id.l10n_in_hsn_code;
        return extraValues;
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                l10n_in_hsn_code: { type: String, optional: true },
            },
        },
    },
});
