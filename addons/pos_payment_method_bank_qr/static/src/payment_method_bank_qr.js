import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

class PaymentMethodBankQr extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return false;
    }

    pollingIntervalMs() {
        return 0;
    }
}

electronicPaymentRegistry.add("bank_qr", PaymentMethodBankQr);
