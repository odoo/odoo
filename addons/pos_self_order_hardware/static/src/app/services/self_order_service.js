import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import LedController from "../class/led_controller";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.ledController = new LedController(this.config);
    },
    handleErrorNotification() {
        super.handleErrorNotification(...arguments);
        this.ledController.setDanger();

        setTimeout(() => {
            this.ledController.setDefault();
        }, 2000);
    },
});
