import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    selectOrderLine(order, line) {
        super.selectOrderLine(order, line);
        // Ensure the numpadMode should be `price` when the discount line is selected
        if (line?.isDiscountLine) {
            this.numpadMode = "price";
        }
    },
});
