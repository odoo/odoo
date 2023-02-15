/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";

export class RefundButton extends LegacyComponent {
    static template = "point_of_sale.RefundButton";

    setup() {
        super.setup();
        this.pos = usePos();
        useListener("click", this._onClick);
    }
    _onClick() {
        const partner = this.env.pos.get_order().get_partner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.pos.showScreen("TicketScreen", {
            ui: { filter: "SYNCED", searchDetails },
            destinationOrder: this.env.pos.get_order(),
        });
    }
}

ProductScreen.addControlButton({
    component: RefundButton,
    condition: function () {
        return true;
    },
});
