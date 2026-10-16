import { PosPaymentMethod } from "@point_of_sale/app/models/pos_payment_method";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosPaymentMethod.prototype, {
    canStartPayment({ paymentline } = {}) {
        if (
            this.payment_provider === "bancontact_pay" &&
            paymentline &&
            paymentline.getAmount() <= 0
        ) {
            return {
                status: false,
                message: _t("The amount must be positive to use this payment method."),
            };
        }
        return super.canStartPayment(...arguments);
    },
    isBlockedBy(line) {
        if (this.payment_provider !== "bancontact_pay") {
            return super.isBlockedBy(...arguments);
        }
        if (this.bancontact_usage === "display") {
            return false;
        }
        if (this.bancontact_usage === "sticker") {
            return line.payment_method_id.id === this.id;
        }
        // Unknown usage
        return super.isBlockedBy(...arguments);
    },
    getBlockingMessage(line) {
        if (this.payment_provider === "bancontact_pay" && this.bancontact_usage === "sticker") {
            return _t("This sticker is already processing another payment.");
        }
        return super.getBlockingMessage(...arguments);
    },
});
