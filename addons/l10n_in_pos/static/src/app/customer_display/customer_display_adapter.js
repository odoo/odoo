import { patch } from "@web/core/utils/patch";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";

patch(CustomerDisplayPosAdapter.prototype, {
    formatOrderData(order) {
        super.formatOrderData(order);
        this.data.onlinePaymentData = { ...(order.onlinePaymentData || {}) };
    },
    getOrderlineData(line) {
        const data = super.getOrderlineData(line);
        data.l10n_in_hsn_code = line.getProduct().l10n_in_hsn_code || "";
        return data;
    },
});
