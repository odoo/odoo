/** @odoo-module */

const { Component } = owl;
import { NavBar } from "../NavBar/NavBar.js";
import { formatMonetary } from "@web/views/fields/formatters";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
// import { session } from "@web/session.js";
export class OrderView extends Component {
    setup() {
        this.formatMonetary = formatMonetary;
        this.selfOrder = useSelfOrder();
    }
    static components = { NavBar };
}
OrderView.template = "OrderView";
export default { OrderView };
