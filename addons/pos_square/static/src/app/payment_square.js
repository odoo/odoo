import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { registry } from "@web/core/registry";

/** Square is driven through its app, this interface only keeps the payment line electronic. */
export class PaymentSquare extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.supports_refunds = false; // Square has no refund request in the Point of Sale API
    }

    async sendPaymentCancel() {
        // Returning true lets the cashier delete the line, the request lives in the Square app.
        return true;
    }
}

registry.category("pos_payment_providers").add("square", PaymentSquare);
