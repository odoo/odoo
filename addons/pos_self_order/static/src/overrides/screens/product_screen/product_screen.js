import { patch } from "@web/core/utils/patch";
import { useQrcodePayment } from "@pos_self_order/overrides/utils/qrcode_payment_mixin";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        useQrcodePayment();
    },
});
