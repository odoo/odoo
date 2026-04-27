import { Order } from "@pos_preparation_display/app/components/order/order";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Order.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.order_status = {
            placed: "Placed",
            acknowledged: "Acknowledged",
            food_ready: "Food Ready",
            dispatched: "Dispatched",
            completed: "Completed",
            cancelled: "Cancelled",
        };
    },

    /**
     * @override
     */
    async doneOrder() {
        super.doneOrder();
        if (this.props.order.delivery_identifier) {
            await this.orm.call("pos.config", "order_status_update", [
                this.props.order.config_id,
                this.props.order.posOrderId,
                "Food Ready",
            ]);
        }
    },
});
