/** @odoo-module */

const { Component } = owl;
import { NavBar } from "../NavBar/NavBar.js";
import { formatMonetary } from "@web/views/fields/formatters";
export class OrderView extends Component {
    setup() {
        this.formatMonetary = formatMonetary;
    }
    static components = { NavBar };
}
OrderView.template = "OrderView";
export default { OrderView };
