/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_store";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class BackToFloorButton extends PosComponent {
    setup() {
        super.setup();
        this.pos = usePos();
    }
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
        this.showScreen("FloorScreen", { floor: this.floor });
    }
}
BackToFloorButton.template = "BackToFloorButton";

Registries.Component.add(BackToFloorButton);

export default BackToFloorButton;
