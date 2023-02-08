/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { usePos } from "@point_of_sale/app/pos_hook";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class SetSaleOrderButton extends Component {
    static template = "SetSaleOrderButton";

    setup() {
        super.setup();
        this.pos = usePos();
        this.rpc = useService("rpc");
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    async click() {
        // ping the server, if no error, show the screen
        // Use rpc from services which resolves even when this
        // component is destroyed (removed together with the popup).
        await this.env.services.rpc({
            model: "sale.order",
            method: "browse",
            args: [[]],
            kwargs: { context: this.env.session.user_context },
        });
        const screen = this.env.isMobile
            ? "MobileSaleOrderManagementScreen"
            : "SaleOrderManagementScreen";
        this.pos.showScreen(screen);
    }
}

ProductScreen.addControlButton({
    component: SetSaleOrderButton,
    condition: function () {
        return true;
    },
});
