import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get isDeliveryLine() {
        const deliveryProductId = this.order_id?.preset_id?.delivery_product_id?.id;
        return Boolean(deliveryProductId) && this.product_id?.id === deliveryProductId;
    },
    isServiceFeeApplicable() {
        return super.isServiceFeeApplicable(...arguments) && !this.isDeliveryLine;
    },
});
