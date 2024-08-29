import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { patch } from "@web/core/utils/patch";

patch(OrderTabs, {
    newFloatingOrder() {
        super.newFloatingOrder();
        this.pos.get_order().setBooked(true);
    },
});
