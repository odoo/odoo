import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.module_pos_hr && this.pos.cashier.employee === null) {
            this.currentOrder.employee_id = this.pos.cashier.employee;
        }

        await super.validateOrder(...arguments);
    },
});
