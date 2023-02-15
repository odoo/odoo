/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService } from "@web/core/utils/hooks";
import { ClosePosPopup } from "@point_of_sale/js/Popups/ClosePosPopup";

// Previously HeaderButtonWidget
// This is the close session button
export class HeaderButton extends LegacyComponent {
    static template = "HeaderButton";

    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
    }

    async onClick() {
        const info = await this.env.pos.getClosePosInfo();
        this.popup.add(ClosePosPopup, { info: info, keepBehind: true });
    }
}
