/* eslint { "no-restricted-syntax": [ "error", {
    "selector": "MemberExpression[object.type=ThisExpression][property.name=pos]",
    "message": "Using this.pos in models is deprecated and about to be removed, for any question ask PoS team." }]}*/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        this.l10n_in_hsn_code = this.product_id.l10n_in_hsn_code;
        return super.setup(...arguments);
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            l10n_in_hsn_code: this.get_product().l10n_in_hsn_code,
        };
    },
});
