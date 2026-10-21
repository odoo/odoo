import { PosPaymentMethod } from "@point_of_sale/app/models/pos_payment_method";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosPaymentMethod.prototype, {
    get paymentInterfaceKey() {
        return this.type === "online" ? this.type : super.paymentInterfaceKey;
    },
    isBlockedBy(line, { order, paymentline }) {
        if (this.type !== "online") {
            return super.isBlockedBy(...arguments);
        }
        // Only sending is blocked, adding another online line is allowed
        return Boolean(
            paymentline && line.payment_method_id.type === "online" && line.pos_order_id === order
        );
    },
    getBlockingMessage(line) {
        if (this.type !== "online") {
            return super.getBlockingMessage(...arguments);
        }
        return _t("Another online payment is already in progress for this order.");
    },
});
