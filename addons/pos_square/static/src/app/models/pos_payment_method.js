import { PosPaymentMethod } from "@point_of_sale/app/models/pos_payment_method";
import { patch } from "@web/core/utils/patch";
import { isAndroid, isIOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

patch(PosPaymentMethod.prototype, {
    usesSquareApp() {
        return this.payment_provider === "square" && (isIOS() || isAndroid());
    },

    getPaymentInterfaceStates() {
        if (this.payment_provider === "square" && !this.usesSquareApp()) {
            return {
                status: false,
                message: _t("Square payments can only be taken from a mobile device."),
            };
        }
        return super.getPaymentInterfaceStates(...arguments);
    },
});
