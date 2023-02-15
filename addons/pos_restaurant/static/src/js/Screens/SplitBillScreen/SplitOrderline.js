/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { LegacyComponent } from "@web/legacy/legacy_component";

export class SplitOrderline extends LegacyComponent {
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
