import { Component } from "@odoo/owl";

export class KioskQuantityWidget extends Component {
    static template = "pos_self_order.KioskQuantityWidget";
    static props = ["value", "onQtyDown", "onQtyUp"];

    setup() {}
}
