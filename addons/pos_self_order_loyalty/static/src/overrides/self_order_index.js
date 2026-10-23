import { selfOrderIndex } from "@pos_self_order/app/self_order_index";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";

patch(selfOrderIndex.prototype, {
    setup() {
        super.setup(...arguments);
        useBarcodeReader({
            client: this.selfOrder._barcodePartnerAction.bind(this.selfOrder),
            coupon: this.selfOrder._barcodeCouponCodeAction.bind(this.selfOrder),
        });
    },
});
