import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

class PaymentMethodMollie extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return true;
    }

    pollingIntervalMs() {
        return 5000;
    }

    _handleTransactionResponse(response) {
        if (response.mollie_test_mode_payment_link) {
            window.open(response.mollie_test_mode_payment_link, "_blank");
        }
        return super._handleTransactionResponse(...arguments);
    }
}

electronicPaymentRegistry.add("mollie", PaymentMethodMollie);
