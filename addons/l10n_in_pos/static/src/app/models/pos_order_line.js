import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        return super.setup(...arguments);
    },
    get l10n_in_hsn_code() {
        return this.product_id?.l10n_in_hsn_code || "";
    },
});
