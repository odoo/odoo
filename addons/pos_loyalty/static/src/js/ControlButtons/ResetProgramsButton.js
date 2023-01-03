/** @odoo-module **/

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";
import { useListener } from "@web/core/utils/hooks";

export class ResetProgramsButton extends PosComponent {
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

ResetProgramsButton.template = "ResetProgramsButton";

ProductScreen.addControlButton({
    component: ResetProgramsButton,
    condition: function () {
        return this.env.pos.programs.some((p) => ["coupons", "promotion"].includes(p.program_type));
    },
});

Registries.Component.add(ResetProgramsButton);
