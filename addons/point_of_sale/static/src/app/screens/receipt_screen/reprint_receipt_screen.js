/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AbstractReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/abstract_receipt_screen";
import { registry } from "@web/core/registry";

export class ReprintReceiptScreen extends AbstractReceiptScreen {
    static template = "point_of_sale.ReprintReceiptScreen";
    static storeOnOrder = false;
    setup() {
        super.setup();
        this.pos = usePos();
    }

    confirm() {
        this.pos.showScreen("TicketScreen", { reuseSavedUIState: true });
    }

    async tryReprint() {
        await this._printReceipt();
    }

    get receiptData() {
        return this.props.order.getOrderReceiptEnv();
    }
}

registry.category("pos_screens").add("ReprintReceiptScreen", ReprintReceiptScreen);
