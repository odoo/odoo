import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { rpc } from "@web/core/network/rpc";

patch(PosOrder.prototype, {
    getCustomerDisplayData() {
        return {
            ...super.getCustomerDisplayData(),
            onlinePaymentData: { ...this.onlinePaymentData },
        };
    },
    set_partner(partner) {
        super.set_partner(...arguments);
        return rpc("/web/dataset/call_kw/pos.order/write", {
            model: "pos.order",
            method: "write",
            args: [this.id, { partner_id: partner ? partner.id : false }],
            kwargs: {},
        });
    },
});
