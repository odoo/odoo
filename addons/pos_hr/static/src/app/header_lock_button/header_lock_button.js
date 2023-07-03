/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class HeaderLockButton extends Component {
    static template = "pos_hr.HeaderLockButton";

    setup() {
        this.pos = usePos();
    }
    async showLoginScreen() {
        this.pos.reset_cashier();
        await this.pos.showTempScreen("LoginScreen");
    }
}
