import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

class PaymentMethodViva extends PaymentMethod {
    supportsRefunds() {
        return true;
    }

    supportsReversals() {
        return true;
    }

    pollingIntervalMs() {
        return 5000;
    }
}

electronicPaymentRegistry.add("viva_com", PaymentMethodViva);
