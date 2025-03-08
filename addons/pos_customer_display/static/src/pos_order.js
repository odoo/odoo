import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    getCustomerDisplayData() {
        const temp = this.getSortedOrderlines().map((l) => ({
            ...l.getDisplayData(),
            isRefund: l.refunded_orderline_id ? true : false,
        }));

        return {
            ...super.getCustomerDisplayData(),
            partner: this.partner_id
                ? {
                    id: this.partner_id.id,
                    name: this.partner_id.name,
                }
                : null,
            amount_per_guest: this.amountPerGuest(),
            refundLines: temp.filter((x) => x.isRefund),
            lines: temp.filter((x) => !x.isRefund),
        };
    },
});
