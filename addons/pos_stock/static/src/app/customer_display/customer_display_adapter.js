import { patch } from "@web/core/utils/patch";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";

patch(CustomerDisplayPosAdapter.prototype, {
    getOrderlineData(line) {
        return {
            ...super.getOrderlineData(...arguments),
            packLotLines: line.packLotLines,
        };
    },
});
