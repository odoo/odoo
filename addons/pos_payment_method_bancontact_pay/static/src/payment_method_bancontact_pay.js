import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

export class PaymentMethodBancontactPay extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return false;
    }

    pollingIntervalMs() {
        return 5000;
    }
}

electronicPaymentRegistry.add("bancontact_pay", PaymentMethodBancontactPay);
