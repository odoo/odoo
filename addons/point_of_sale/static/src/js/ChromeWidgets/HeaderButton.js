/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { ClosePosPopup } from "../Popups/ClosePosPopup";

// Previously HeaderButtonWidget
// This is the close session button
export class HeaderButton extends PosComponent {
    static template = "HeaderButton";

    async onClick() {
        const info = await this.env.pos.getClosePosInfo();
        this.showPopup(ClosePosPopup, { info: info, keepBehind: true });
    }
}
