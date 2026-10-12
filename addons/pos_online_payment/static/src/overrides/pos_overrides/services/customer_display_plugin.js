import { patch } from "@web/core/utils/patch";
import { CustomerDisplayTerminalPlugin } from "@point_of_sale/app/plugins/customer_display_terminal_plugin";

patch(CustomerDisplayTerminalPlugin.prototype, {
    _buildDisplayPayload(order) {
        return {
            ...super._buildDisplayPayload(order),
            onlinePaymentData: { ...(order.onlinePaymentData || {}) },
        };
    },
});
