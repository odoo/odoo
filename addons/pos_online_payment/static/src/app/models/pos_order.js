import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get isCustomerRequired() {
        const online_payments_customer_required = this.paymentsRequireCustomer(this.payment_ids);
        return super.isCustomerRequired || (!this.partner_id && online_payments_customer_required);
    },
    paymentsRequireCustomer(payments) {
        return payments?.some(
            (payment) =>
                payment.payment_method_id.type === "online" &&
                payment.payment_method_id._customer_required
        );
    },
});
