import { PosPaymentMethod } from "@point_of_sale/app/models/pos_payment_method";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosPaymentMethod.prototype, {
    get paymentProviderKey() {
        return this.type === "online" ? this.type : super.paymentProviderKey;
    },
    _checkOrder({ order, paymentline }) {
        if (this.type !== "online") {
            return super._checkOrder(...arguments);
        }
        const hasProcessingOnlinePayment =
            paymentline?.pos_order_id === order &&
            order.payment_ids.some(
                (pl) =>
                    pl.payment_method_id.type === "online" &&
                    pl.uuid !== paymentline.uuid &&
                    pl.isProcessing
            );
        if (hasProcessingOnlinePayment) {
            return {
                status: false,
                message: _t("Another online payment is already in progress for this order."),
            };
        }
        return { status: true, message: "" };
    },
});
