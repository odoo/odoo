import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
    },

    async sendToPick() {
        const currentOrder = this.pos.get_order();
        if (!currentOrder?.select_date) {
            const today = new Date().toISOString().split("T")[0];
            currentOrder.select_date = today;
            this.notification.add(_t("Shipping date set to: ") + today, {
                type: "success",
            });
            await this.pos.syncAllOrders(currentOrder);
        } else {
            currentOrder.select_date = false;
        }
    },
});
