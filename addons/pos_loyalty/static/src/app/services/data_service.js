import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    async loadServerOrders(domain) {
        // Loyalty cards created by an ongoing order only exist locally (negative id),
        // so the server returns its reward lines without coupon: keep the local link.
        const localCouponByLineUuid = Object.fromEntries(
            this.models["pos.order.line"]
                .filter((line) => line.coupon_id?.id < 0)
                .map((line) => [line.uuid, line.coupon_id])
        );
        const orders = await super.loadServerOrders(domain);
        for (const line of orders.flatMap((order) => order.lines)) {
            if (!line.coupon_id && line.uuid in localCouponByLineUuid) {
                line.coupon_id = localCouponByLineUuid[line.uuid];
            }
        }
        return orders;
    },
});
