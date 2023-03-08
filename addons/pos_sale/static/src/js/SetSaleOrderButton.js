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
        this.orm = useService("orm");
    }
    async click() {
        // FIXME POSREF why are we calling browse for a ping?
        // Why don't we let the order management screen deal with the offline error?
        await this.orm.call("sale.order", "browse", [[]]);
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
