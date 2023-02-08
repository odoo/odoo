/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class Orderline extends LegacyComponent {
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
