/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        if (this.company.country_id?.code === "IN") {
            this.l10n_in_hsn_code = this.product_id.l10n_in_hsn_code;
        }
        return super.setup(...arguments);
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            l10n_in_hsn_code: this.product_id.l10n_in_hsn_code,
        };
    },
});
