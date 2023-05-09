/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class HeaderLockButton extends Component {
    static template = "HeaderLockButton";

    setup() {
        super.setup();
        this.pos = usePos();
    }
    async showLoginScreen() {
        this.pos.globalState.reset_cashier();
        await this.pos.showTempScreen("LoginScreen");
    }
}
