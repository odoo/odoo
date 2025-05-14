import { Component } from "@odoo/owl";

export class QuantityWidget extends Component {
    static template = "pos_self_order.QuantityWidget";
    static props = ["value", "onQtyDown", "onQtyUp"];

    setup() {}
}
