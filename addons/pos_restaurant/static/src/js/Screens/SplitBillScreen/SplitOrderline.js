/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class SplitOrderline extends PosComponent {
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
SplitOrderline.template = "SplitOrderline";

Registries.Component.add(SplitOrderline);

export default SplitOrderline;
