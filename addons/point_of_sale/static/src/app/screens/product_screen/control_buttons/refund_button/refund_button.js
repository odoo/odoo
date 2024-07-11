/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";

export class RefundButton extends Component {
    static template = "point_of_sale.RefundButton";

    setup() {
        this.pos = usePos();
    }
    click() {
        const order = this.pos.get_order();
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
