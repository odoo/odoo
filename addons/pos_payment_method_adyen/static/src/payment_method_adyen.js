import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

class PaymentMethodAdyen extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return true;
    }

    pollingIntervalMs() {
        return 5000;
    }
}

electronicPaymentRegistry.add("adyen", PaymentMethodAdyen);
