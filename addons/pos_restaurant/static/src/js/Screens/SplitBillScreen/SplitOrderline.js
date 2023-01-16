/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { PosComponent } from "@point_of_sale/js/PosComponent";

export class SplitOrderline extends PosComponent {
    static template = "SplitOrderline";

    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    get isSelected() {
        return this.props.split.quantity !== 0;
    }
    onClick() {
        this.trigger("click-line", this.props.line);
    }
}
