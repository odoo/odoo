import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.module_pos_hr) {
            this.order.employee_id = this.pos.getCashier();
        }

        await super.validateOrder(...arguments);
    },
});
