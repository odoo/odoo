/** @odoo-module */

const { Component } = owl;
import { NavBar } from "../NavBar/NavBar.js";
import { AlertMessage } from "../AlertMessage/AlertMessage.js";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
export class CartView extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
    }
    static components = { NavBar, AlertMessage };
}
CartView.template = "CartView";
export default { CartView };
