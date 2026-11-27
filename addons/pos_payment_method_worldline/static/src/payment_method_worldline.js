import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

class PaymentMethodWorldline extends PaymentMethod {
    supportsRefunds() {
        return true;
    }

    supportsReversals() {
        return false;
    }

    pollingIntervalMs() {
        return 5000;
    }
}

electronicPaymentRegistry.add("worldline", PaymentMethodWorldline);
