/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AbstractReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/abstract_receipt_screen";
import { registry } from "@web/core/registry";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt";

export class ReprintReceiptScreen extends AbstractReceiptScreen {
    static template = "point_of_sale.ReprintReceiptScreen";
    static components = { OrderReceipt };
    static storeOnOrder = false;
    setup() {
        super.setup();
        this.pos = usePos();
        owl.onMounted(this.onMounted);
    }
    onMounted() {
        this.printReceipt();
    }
    confirm() {
        this.pos.showScreen("TicketScreen", { reuseSavedUIState: true });
    }
    async printReceipt() {
        const { iface_print_skip_screen } = this.pos.config;
        if (this.hardwareProxy.printer && iface_print_skip_screen) {
            const result = await this._printReceipt();
            if (result) {
                this.pos.showScreen("TicketScreen", { reuseSavedUIState: true });
            }
        }
    }
    async tryReprint() {
        await this._printReceipt();
    }
}

registry.category("pos_screens").add("ReprintReceiptScreen", ReprintReceiptScreen);
