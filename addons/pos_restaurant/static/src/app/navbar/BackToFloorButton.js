/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class BackToFloorButton extends Component {
    static template = "BackToFloorButton";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
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
