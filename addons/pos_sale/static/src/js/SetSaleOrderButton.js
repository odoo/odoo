/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import { Gui } from "@point_of_sale/js/Gui";

export class SetSaleOrderButton extends PosComponent {
    static template = "SetSaleOrderButton";

    setup() {
        super.setup();
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
        // LegacyComponent doesn't work the same way as before.
        // We need to use Gui here to show the screen. This will work
        // because ui methods in Gui is bound to the root component.
        const screen = this.env.isMobile
            ? "MobileSaleOrderManagementScreen"
            : "SaleOrderManagementScreen";
        Gui.showScreen(screen);
    }
}

ProductScreen.addControlButton({
    component: SetSaleOrderButton,
    condition: function () {
        return true;
    },
});
