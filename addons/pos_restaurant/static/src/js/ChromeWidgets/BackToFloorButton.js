/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

/**
 * Props: {
 *     onClick: callback
 * }
 */
class BackToFloorButton extends PosComponent {
    get table() {
        return this.env.pos.table;
    }
    get floor() {
        return this.table ? this.table.floor : null;
    }
    get hasTable() {
        return this.table != null;
    }
    backToFloorScreen() {
        if (this.props.onClick) {
            this.props.onClick();
        }
        this.showScreen("FloorScreen", { floor: this.floor });
    }
}
BackToFloorButton.template = "BackToFloorButton";

Registries.Component.add(BackToFloorButton);

export default BackToFloorButton;
