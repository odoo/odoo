import { registry } from "@web/core/registry";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";

export class PaymentBankQr extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.supports_refunds = false;
        this.auto_send_request = true;
    }

    async sendPaymentRequest(line) {
        return await this.pos.showQR(line);
    }

    async sendPaymentCancel(line) {
        return true;
    }
}

registry.category("pos_payment_providers").add("bank_qr_code", PaymentBankQr);
