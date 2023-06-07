/** @odoo-module */

import { Component } from "@odoo/owl";

export class SplitOrderline extends Component {
    static template = "pos_restaurant.SplitOrderline";

    setup() {}
    get isSelected() {
        return this.props.split.quantity !== 0;
    }
    click() {
        this.props.onClickLine(this.props.line);
    }
}
