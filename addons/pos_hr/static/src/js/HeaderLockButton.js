/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

const { useState } = owl;

export class HeaderLockButton extends PosComponent {
    static template = "HeaderLockButton";

    setup() {
        super.setup();
        this.state = useState({ isUnlockIcon: true, title: "Unlocked" });
    }
    async showLoginScreen() {
        this.env.pos.reset_cashier();
        await this.showTempScreen("LoginScreen");
    }
    onMouseOver(isMouseOver) {
        this.state.isUnlockIcon = !isMouseOver;
        this.state.title = isMouseOver ? "Lock" : "Unlocked";
    }
}
