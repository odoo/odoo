/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class BackToFloorButton extends Component {
    static template = "BackToFloorButton";

    setup() {
        super.setup();
        this.pos = usePos();
    }
    get table() {
        return this.pos.globalState.table;
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
