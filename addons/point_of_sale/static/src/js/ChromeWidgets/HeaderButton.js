/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

// Previously HeaderButtonWidget
// This is the close session button
class HeaderButton extends PosComponent {
    async onClick() {
        const info = await this.env.pos.getClosePosInfo();
        this.showPopup("ClosePosPopup", { info: info, keepBehind: true });
    }
}
HeaderButton.template = "HeaderButton";

Registries.Component.add(HeaderButton);

export default HeaderButton;
