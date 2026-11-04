import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";

export class EatingLocationPage extends Component {
    static template = "pos_self_order.EatingLocationPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
    }

    back() {
        this.router.navigate("default");
    }

    selectLocation(loc) {
        this.selfOrder.currentOrder.takeaway = loc === "out";
        this.selfOrder.orderTakeAwayState[this.selfOrder.currentOrder.uuid] = true;

        if (loc === "out") {
            this.selfOrder.currentOrder.update({
                fiscal_position_id: this.selfOrder.config.takeaway_fp_id,
            });
        }
        this.router.navigate("product_list");
    }
}
