/** @odoo-module */

import { Component } from "@odoo/owl";

export class SplitOrderline extends Component {
    static template = "SplitOrderline";

    setup() {
        super.setup();
    }
    get isSelected() {
        return this.props.split.quantity !== 0;
    }
    click() {
        this.props.onClickLine(this.props.line);
    }
}
