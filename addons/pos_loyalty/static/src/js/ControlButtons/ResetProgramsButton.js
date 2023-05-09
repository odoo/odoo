/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class ResetProgramsButton extends Component {
    static template = "ResetProgramsButton";

    setup() {
        this.pos = usePos();
    }
    _isDisabled() {
        return !this.pos.globalState.get_order().isProgramsResettable();
    }
    click() {
        this.pos.globalState.get_order()._resetPrograms();
    }
}

ProductScreen.addControlButton({
    component: ResetProgramsButton,
    condition: function () {
        return this.pos.globalState.programs.some((p) =>
            ["coupons", "promotion"].includes(p.program_type)
        );
    },
});
