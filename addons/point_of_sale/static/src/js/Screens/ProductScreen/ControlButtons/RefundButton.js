/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class RefundButton extends Component {
    static template = "point_of_sale.RefundButton";

    setup() {
        this.pos = usePos();
    }
    click() {
        const order = this.pos.globalState.get_order();
        const partner = order.get_partner();
        const searchDetails = partner ? { fieldName: "PARTNER", searchTerm: partner.name } : {};
        this.pos.showScreen("TicketScreen", {
            ui: { filter: "SYNCED", searchDetails },
            destinationOrder: order,
        });
    }
}

ProductScreen.addControlButton({
    component: RefundButton,
    condition: function () {
        return true;
    },
});
