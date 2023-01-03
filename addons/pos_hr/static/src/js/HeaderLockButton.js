/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

const { useState } = owl;

class HeaderLockButton extends PosComponent {
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
HeaderLockButton.template = "HeaderLockButton";

Registries.Component.add(HeaderLockButton);

export default HeaderLockButton;
