import { PosPaymentMethod } from "@point_of_sale/app/models/pos_payment_method";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosPaymentMethod.prototype, {
    _checkOrder({ order, paymentline }) {
        if (this.payment_provider !== "bancontact_pay") {
            return super._checkOrder(...arguments);
        }

        // Check amount
        if (paymentline && paymentline.getAmount() <= 0) {
            return {
                status: false,
                message: _t("The amount must be positive to use this payment method."),
            };
        }

        // Display
        if (this.bancontact_usage === "display") {
            return { status: true, message: "" };
        }

        // Sticker
        if (this.bancontact_usage === "sticker") {
            const hasProcessingPaymentSameSticker = order.payment_ids.some(
                (pl) =>
                    pl.payment_method_id.id === this.id &&
                    pl.uuid !== paymentline?.uuid &&
                    pl.isProcessing()
            );
            if (hasProcessingPaymentSameSticker) {
                return {
                    status: false,
                    message: _t("This sticker is already processing another payment."),
                };
            }
            return { status: true, message: "" };
        }

        // Unknown usage
        return super._checkOrder(...arguments);
    },
});
