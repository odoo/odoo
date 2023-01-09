/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import Registries from "@point_of_sale/js/Registries";

class PrintBillButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    _isDisabled() {
        const order = this.env.pos.get_order();
        return order.get_orderlines().length === 0;
    }
    onClick() {
        this.showTempScreen("BillScreen");
    }
}
PrintBillButton.template = "PrintBillButton";

ProductScreen.addControlButton({
    component: PrintBillButton,
    condition: function () {
        return this.env.pos.config.iface_printbill;
    },
});

Registries.Component.add(PrintBillButton);

export default PrintBillButton;
