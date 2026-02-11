import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    canBeValidated() {
        const hasOnlinePayment = this.payment_ids?.some(
            (p) => p?.payment_method_id?.is_online_payment
        );
        if (hasOnlinePayment && typeof this.id !== "number") {
            return false;
        }
        return super.canBeValidated();
    },
    get isCustomerRequired() {
        if (this.partner_id) {
            return false;
        }
        const online_payments_customer_required = this.payment_requires_customer(this.payment_ids);

        const res = super.isCustomerRequired;
        return res || online_payments_customer_required;
    },
    payment_requires_customer(payments) {
        return payments?.some(
            (payment) =>
                payment.payment_method_id.is_online_payment &&
                payment.payment_method_id._customer_required
        );
    },
});
