/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { PosComponent } from "@point_of_sale/js/PosComponent";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";

export class SplitBillButton extends PosComponent {
    static template = "SplitBillButton";

    setup() {
        super.setup();
        this.pos = usePos();
        useListener("click", this.onClick);
    }
    _isDisabled() {
        const order = this.env.pos.get_order();
        return (
            order
                .get_orderlines()
                .reduce((totalProduct, orderline) => totalProduct + orderline.quantity, 0) < 2
        );
    }
    async onClick() {
        this.pos.showScreen("SplitBillScreen");
    }
}

ProductScreen.addControlButton({
    component: SplitBillButton,
    condition: function () {
        return this.env.pos.config.iface_splitbill;
    },
});
