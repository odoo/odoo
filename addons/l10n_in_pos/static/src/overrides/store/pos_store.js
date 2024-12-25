/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getReceiptHeaderData() {
        return {
            ...super.getReceiptHeaderData(...arguments),
            partner: this.selectedOrder.partner,
        };
    },
});
