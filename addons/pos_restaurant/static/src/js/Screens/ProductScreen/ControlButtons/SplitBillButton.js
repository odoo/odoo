/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import Registries from "@point_of_sale/js/Registries";

class SplitBillButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    _isDisabled() {
        const order = this.env.pos.get_order();
        return (
            order
                .get_orderlines()
                .reduce((totalProduct, orderline) => totalProduct + orderline.quantity, 0) < 2
        );
    }
    async onClick() {
        this.showScreen("SplitBillScreen");
    }
}
SplitBillButton.template = "SplitBillButton";

ProductScreen.addControlButton({
    component: SplitBillButton,
    condition: function () {
        return this.env.pos.config.iface_splitbill;
    },
});

Registries.Component.add(SplitBillButton);

export default SplitBillButton;
