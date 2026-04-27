import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { getTime } from "@pos_urban_piper/utils";

patch(PosOrder.prototype, {
    get deliveryTime() {
        const deliveryJson = JSON.parse(this.delivery_json);
        return getTime(deliveryJson.order?.details?.delivery_datetime);
    },
    isFutureOrder() {
        if (this.delivery_datetime) {
            return true;
        }
        return super.isFutureOrder();
    },
});
