/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { PosComponent } from "@point_of_sale/js/PosComponent";

export class BackToFloorButton extends PosComponent {
    static template = "BackToFloorButton";

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
        this.pos.showScreen("FloorScreen", { floor: this.floor });
    }
}
