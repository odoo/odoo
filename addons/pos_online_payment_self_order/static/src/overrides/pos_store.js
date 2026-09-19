import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        if (
            this.config.self_ordering_mode === "mobile" &&
            this.config.self_ordering_pay_after !== "meal"
        ) {
            this.data.connectWebSocket("ONLINE_PAYMENT_STATUS", (notification) => {
                if (notification.status === "success") {
                    this._handleSelfOrder(notification.order_id);
                }
            });
        }
    },
});
