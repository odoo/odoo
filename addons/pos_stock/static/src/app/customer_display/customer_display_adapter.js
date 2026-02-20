import { patch } from "@web/core/utils/patch";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";

patch(CustomerDisplayPosAdapter.prototype, {
    getOrderlineData(line) {
        const order_line_data = super.getOrderlineData(line);
        return {
            ...order_line_data,
            packLotLines: line.packLotLines,
        };
    },
});
