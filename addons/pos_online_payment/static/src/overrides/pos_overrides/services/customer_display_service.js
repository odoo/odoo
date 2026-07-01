import { patch } from "@web/core/utils/patch";
import { CustomerDisplayService } from "@point_of_sale/customer_display/customer_display_service";

patch(CustomerDisplayService.prototype, {
    _buildDisplayPayload(order) {
        return {
            ...super._buildDisplayPayload(order),
            onlinePaymentData: { ...(order.onlinePaymentData || {}) },
        };
    },
});
