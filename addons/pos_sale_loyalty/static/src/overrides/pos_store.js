import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    getConvertedQuantityFromSaleOrderline(convertedLine, soLine) {
        // we need to consider reward product such as discount in a quotation
        if (soLine.reward_id) {
            return soLine.product_uom_qty;
        } else {
            return super.getConvertedQuantityFromSaleOrderline(...arguments);
        }
    },
});
