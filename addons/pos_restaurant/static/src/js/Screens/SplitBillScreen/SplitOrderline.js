/** @odoo-module */

import { Component } from "@odoo/owl";

export class SplitOrderline extends Component {
    static template = "SplitOrderline";
    static props = {
        onClickLine: Function,
        line: Object,
        split: Object,
    };

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
