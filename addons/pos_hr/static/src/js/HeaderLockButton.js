/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { PosComponent } from "@point_of_sale/js/PosComponent";

const { useState } = owl;

export class HeaderLockButton extends PosComponent {
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
