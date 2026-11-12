import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";

export class PaymentMethodBankQr extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return false;
    }

    pollingIntervalMs() {
        return 0;
    }

    supportsBackendConfirmation() {
        return false;
    }

    async _initPaymentMethod() {
        this.qrProviderDetails = await super._initPaymentMethod();
    }

    setup() {
        super.setup(...arguments);
        this._initPaymentMethod();
    }

    async getTransactionStatus(transactionId) {
        if (this.supportsBackendConfirmation()) {
            return await super.getTransactionStatus(...arguments);
        }
        const result = { transaction_id: transactionId, status: "paid" };
        this._handlePaymentResponse({ transaction_id: transactionId, status: "paid" });
        return result;
    }

    cancelTransaction(transactionId) {
        this._handlePaymentResponse({ transaction_id: transactionId, status: "failed" });
        return { transaction_id: transactionId };
    }
}

electronicPaymentRegistry.add("bank_qr", PaymentMethodBankQr);
