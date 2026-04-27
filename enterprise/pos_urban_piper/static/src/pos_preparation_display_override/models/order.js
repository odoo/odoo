import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/models/order";

patch(Order.prototype, {
    setup(order) {
        super.setup(order);
        this.delivery_status = order.delivery_status;
        this.delivery_provider_id = order.delivery_provider_id;
        this.delivery_identifier = order.delivery_identifier;
        this.prep_time = order.prep_time;
        this.order_otp = order.order_otp;
        this.config_id = order.config_id;
    },

    computeDuration() {
        if (this.delivery_identifier) {
            const total_order_time = luxon.DateTime.fromFormat(
                this.createDate,
                "yyyy-MM-dd HH:mm:ss",
                {
                    zone: "utc",
                }
            )
                .setZone("local")
                .plus({ minutes: this.prep_time || 0 });
            return Math.max(
                Math.round((total_order_time.ts - luxon.DateTime.now().ts) / (1000 * 60)),
                0
            );
        }
        return super.computeDuration();
    },
});
