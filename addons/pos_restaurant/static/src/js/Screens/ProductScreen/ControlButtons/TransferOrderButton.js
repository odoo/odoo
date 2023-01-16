/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";

export class TransferOrderButton extends PosComponent {
    static template = "TransferOrderButton";

    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    async onClick() {
        this.env.pos.setCurrentOrderToTransfer();
        this.showScreen("FloorScreen");
    }
}

ProductScreen.addControlButton({
    component: TransferOrderButton,
    condition: function () {
        return this.env.pos.config.iface_floorplan;
    },
});
