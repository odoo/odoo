/** @odoo-module */

import { PosGlobalState, Order } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "pos_proforma.PosGlobalState", {
    async push_pro_forma_order(order) {
        order.receipt_type = "PS";
        await this.env.pos.push_single_order(order);
        order.receipt_type = false;
    },
});

patch(Order.prototype, "pos_proforma.Order", {
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        json.receipt_type = this.receipt_type;
        return json;
    }
});
