/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { registry } from "@web/core/registry";

export class BillScreen extends ReceiptScreen {
    static template = "pos_restaurant.BillScreen";
    confirm() {
        if (!this.env.isMobile) {
            this.props.resolve({ confirmed: true, payload: null });
            this.pos.closeTempScreen();
        }
    }
    /**
     * @override
     */
    async printReceipt() {
        await super.printReceipt();
        this.currentOrder._printed = false;
    }

    get isBill() {
        return true;
    }

    get receiptData() {
        return this.pos.get_order().getOrderReceiptEnv();
    }
}

registry.category("pos_screens").add("BillScreen", BillScreen);
