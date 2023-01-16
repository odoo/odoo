/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class Orderline extends PosComponent {
    static template = "Orderline";

    selectLine() {
        this.trigger("select-line", { orderline: this.props.line });
    }
    lotIconClicked() {
        this.trigger("edit-pack-lot-lines", { orderline: this.props.line });
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
