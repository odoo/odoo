/** @odoo-module */

import { Component } from "@odoo/owl";

export class Orderline extends Component {
    static template = "Orderline";

    selectLine() {
        this.props.selectLine(this.props.line);
    }
    lotIconClicked() {
        this.props.editPackLotLines(this.props.line);
    }
    get addedClasses() {
        return {
            selected: this.props.line.selected,
        };
    }
    get customerNote() {
        return this.props.line.get_customer_note();
    }
}
