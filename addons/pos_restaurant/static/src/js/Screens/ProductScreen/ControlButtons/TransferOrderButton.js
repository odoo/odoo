/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";

export class TransferOrderButton extends LegacyComponent {
    static template = "TransferOrderButton";

    setup() {
        super.setup();
        this.pos = usePos();
        useListener("click", this.onClick);
    }
    async onClick() {
        this.env.pos.setCurrentOrderToTransfer();
        this.pos.showScreen("FloorScreen");
    }
}

ProductScreen.addControlButton({
    component: TransferOrderButton,
    condition: function () {
        return this.env.pos.config.iface_floorplan;
    },
});
