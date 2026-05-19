/** @odoo-module */

import "@pos_loyalty/app/models/pos_order_line";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const values = super.prepareBaseLineForTaxesComputationExtraValues(...arguments);
        if (this.order_id.company.country_id?.code === "PE" && this.isGiftCardOrEWalletReward?.()) {
            values.special_mode = "total_included";
        }
        return values;
    },
});
