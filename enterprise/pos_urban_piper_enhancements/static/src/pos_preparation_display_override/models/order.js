import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/models/order";
import { getTime } from "@pos_urban_piper/utils";

patch(Order.prototype, {
    setup(order) {
        super.setup(order);
        if (order.delivery_datetime) {
            this.delivery_datetime = getTime(order.delivery_datetime);
        }
    },
});
