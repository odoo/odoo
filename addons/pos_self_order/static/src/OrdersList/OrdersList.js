/** @odoo-module */

const { Component } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { OrderView } from "../OrderView/OrderView.js";

export class OrdersList extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
    }
    static components = { OrderView };
}
OrdersList.template = "OrdersList";
export default { OrdersList };
