/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class BackButton extends Component {
    static template = "point_of_sale.BackButton";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
    async backToFloorScreen() {
        this.pos.mobile_pane = "right";
        this.pos.showScreen("ProductScreen");
    }
}
