/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class ResetProgramsButton extends Component {
    static template = "pos_loyalty.ResetProgramsButton";

    setup() {
        this.pos = usePos();
    }
    _isDisabled() {
        return !this.pos.get_order().isProgramsResettable();
    }
    click() {
        this.pos.get_order()._resetPrograms();
    }
}

ProductScreen.addControlButton({
    component: ResetProgramsButton,
    condition: function () {
        return this.pos.programs.some((p) =>
            ["coupons", "promotion"].includes(p.program_type)
        );
    },
});
