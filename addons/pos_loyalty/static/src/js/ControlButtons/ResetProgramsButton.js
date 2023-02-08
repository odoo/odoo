/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class ResetProgramsButton extends Component {
    static template = "ResetProgramsButton";

    setup() {
        super.setup();
    }
    _isDisabled() {
        return !this.env.pos.get_order().isProgramsResettable();
    }
    click() {
        this.env.pos.get_order()._resetPrograms();
    }
}

ProductScreen.addControlButton({
    component: ResetProgramsButton,
    condition: function () {
        return this.env.pos.programs.some((p) => ["coupons", "promotion"].includes(p.program_type));
    },
});
