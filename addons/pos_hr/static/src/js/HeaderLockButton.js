/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class HeaderLockButton extends Component {
    static template = "HeaderLockButton";

    setup() {
        super.setup();
        this.state = useState({ isUnlockIcon: true, title: "Unlocked" });
        this.pos = usePos();
    }
    async showLoginScreen() {
        this.env.pos.reset_cashier();
        await this.pos.showTempScreen("LoginScreen");
    }
    onMouseOver(isMouseOver) {
        this.state.isUnlockIcon = !isMouseOver;
        this.state.title = isMouseOver ? "Lock" : "Unlocked";
    }
}
