/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { renderToElement } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

export class PrintBillButton extends Component {
    static template = "pos_restaurant.PrintBillButton";

    setup() {
        this.pos = usePos();
        this.hardwareProxy = useService("hardware_proxy");
        this.click = useAsyncLockedMethod(this.click);
    }

    _isDisabled() {
        const order = this.pos.get_order();
        if (!order) {
            return false;
        }
        return order.get_orderlines().length === 0;
    }

    async click() {
        if (this.hardwareProxy.printer) {
            const orderReceipt = renderToElement("point_of_sale.OrderReceipt", {
                receiptData: {
                    ...this.pos.get_order().getOrderReceiptEnv(),
                },
                pos: this.pos,
                env: this.env,
            });

            // Need to await to have the result in case of automatic skip screen.
            await this.hardwareProxy.printer.printReceipt(orderReceipt);
        } else {
            this.pos.showTempScreen("BillScreen");
        }
    }
}

ProductScreen.addControlButton({
    component: PrintBillButton,
    condition: function () {
        return this.pos.config.iface_printbill;
    },
});
