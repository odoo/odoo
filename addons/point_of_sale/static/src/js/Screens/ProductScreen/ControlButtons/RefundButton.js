/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";
import { useListener } from "@web/core/utils/hooks";

class RefundButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this._onClick);
    }
    _onClick() {
        const partner = this.env.pos.get_order().get_partner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.showScreen("TicketScreen", {
            ui: { filter: "SYNCED", searchDetails },
            destinationOrder: this.env.pos.get_order(),
        });
    }
}
RefundButton.template = "point_of_sale.RefundButton";

ProductScreen.addControlButton({
    component: RefundButton,
    condition: function () {
        return true;
    },
});

Registries.Component.add(RefundButton);

export default RefundButton;
