import { patch } from "@web/core/utils/patch";
import { PaymentMethodBankQr } from "@pos_payment_method_bank_qr/payment_method_bank_qr";

patch(PaymentMethodBankQr.prototype, {
    pollingIntervalMs() {
        if (this.qrProviderDetails.qr_code_method === "id_qr") {
            return 5000;
        }
        return super.pollingIntervalMs(...arguments);
    },

    supportsBackendConfirmation() {
        if (this.qrProviderDetails.qr_code_method === "id_qr") {
            return true;
        }
        return super.supportsBackendConfirmation(...arguments);
    },
});
