/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { ClosePosPopup } from "@point_of_sale/js/Popups/ClosePosPopup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

// Previously HeaderButtonWidget
// This is the close session button
export class HeaderButton extends Component {
    static template = "HeaderButton";

    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.popup = useService("popup");
    }

    async onClick() {
        const info = await this.pos.globalState.getClosePosInfo();
        this.popup.add(ClosePosPopup, { info: info, keepBehind: true });
    }
}
