/** @odoo-module **/

import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";

export class ResetProgramsButton extends LegacyComponent {
    static template = "ResetProgramsButton";

    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    _isDisabled() {
        return !this.env.pos.get_order().isProgramsResettable();
    }
    onClick() {
        this.env.pos.get_order()._resetPrograms();
    }
}

ProductScreen.addControlButton({
    component: ResetProgramsButton,
    condition: function () {
        return this.env.pos.programs.some((p) => ["coupons", "promotion"].includes(p.program_type));
    },
});
