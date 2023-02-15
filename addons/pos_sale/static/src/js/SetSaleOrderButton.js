/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/pos_hook";

export class SetSaleOrderButton extends LegacyComponent {
    static template = "SetSaleOrderButton";

    setup() {
        super.setup();
        this.pos = usePos();
        useListener("click", this.onClick);
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    async onClick() {
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
