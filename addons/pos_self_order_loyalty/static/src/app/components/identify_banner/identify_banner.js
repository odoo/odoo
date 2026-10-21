import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
export class IdentifyBanner extends Component {
    static template = "pos_self_order_loyalty.IdentifyBanner";

    setup() {
        this.selfOrder = useSelfOrder();
    }

    onClick() {
        this.selfOrder.identifyCustomer();
    }
}
