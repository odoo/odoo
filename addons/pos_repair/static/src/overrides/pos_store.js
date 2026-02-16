import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    getConvertedQuantityFromSaleOrderline(convertedLine, soLine) {
        // we need to consider repair line such as discount in a quotation
        if (soLine.is_repair_line) {
            return convertedLine.product_uom_qty;
        } else {
            return super.getConvertedQuantityFromSaleOrderline(...arguments);
        }
    },
});
