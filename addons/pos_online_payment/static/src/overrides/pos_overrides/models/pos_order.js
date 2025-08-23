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
    async set_partner(partner) {
        super.set_partner(...arguments);
        if (typeof this.id === "number") {
            await rpc("/web/dataset/call_kw/pos.order/write", {
                model: "pos.order",
                method: "write",
                args: [this.id, { partner_id: partner ? partner.id : false }],
                kwargs: {},
            });
        }
    },
});
