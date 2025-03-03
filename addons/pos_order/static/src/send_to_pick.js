import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async checkOrderPickingStatus(order_id) {
        const result = await this.orm.call("pos.order","check_existing_picking",["pos.order", order_id]);
        return result;
    },

    async sendToPick() {
        const currentOrder = this.pos.get_order();
        if (!currentOrder) return;
        
        const { hasPicking, trackingNumber } = await this.checkOrderPickingStatus(currentOrder.access_token);
        if (hasPicking) {
            this.notification.add(_t(`Order Already Processed. This order already has a picking associated with it.
                Tracking Number : (${trackingNumber})`), {
                type: "danger",
            })
            return;
        }

        if (!currentOrder.partner_id) {
            this.notification.add(_t(`Select Customer`), {
                type: "warning",
            })
            return;
        }

        if (!currentOrder.shipping_date) {
            const today = new Date().toISOString().split("T")[0];
            currentOrder.shipping_date = today;
        }

        const syncOrderResult = await this.pos.push_single_order(currentOrder);

        await this.orm.call("pos.order", "create_picking_set_shipping", ["pos.order" , syncOrderResult[0].id]);
        
        this.notification.add(_t("Order Sent to Pick"), {
            type: "success",
        });
    },
});
