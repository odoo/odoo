/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class Orderline extends PosComponent {
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
Orderline.template = "Orderline";

Registries.Component.add(Orderline);

export default Orderline;
