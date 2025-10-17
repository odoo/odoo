import { patch } from "@web/core/utils/patch";
import { useQrcodePayment } from "@pos_self_order/overrides/utils/qrcode_payment_mixin";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";

patch(FloorScreen.prototype, {
    setup() {
        super.setup(...arguments);
        useQrcodePayment();
    },
});
