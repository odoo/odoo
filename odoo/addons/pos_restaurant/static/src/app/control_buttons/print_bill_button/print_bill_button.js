/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

export class PrintBillButton extends Component {
    static template = "pos_restaurant.PrintBillButton";

    setup() {
        this.pos = usePos();
        this.printer = useService("printer");
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
        // Need to await to have the result in case of automatic skip screen.
        (await this.printer.print(OrderReceipt, {
            data: this.pos.get_order().export_for_printing(),
            formatCurrency: this.env.utils.formatCurrency,
        })) || this.pos.showTempScreen("BillScreen");
    }
}

ProductScreen.addControlButton({
    component: PrintBillButton,
    condition: function () {
        return this.pos.config.iface_printbill;
    },
});
