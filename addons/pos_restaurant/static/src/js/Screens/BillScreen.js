/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/js/Screens/ReceiptScreen/ReceiptScreen";
import { registry } from "@web/core/registry";

<<<<<<< HEAD
export class BillScreen extends ReceiptScreen {
    static template = "pos_restaurant.BillScreen";
    confirm() {
        this.props.resolve({ confirmed: true, payload: null });
        this.pos.closeTempScreen();
||||||| parent of 8dbfd93303f (temp)
const BillScreen = (ReceiptScreen) => {
    class BillScreen extends ReceiptScreen {
        confirm() {
            this.props.resolve({ confirmed: true, payload: null });
            this.trigger("close-temp-screen");
        }
        whenClosing() {
            this.confirm();
        }
        /**
         * @override
         */
        async printReceipt() {
            await super.printReceipt();
            this.currentOrder._printed = false;
        }
=======
const BillScreen = (ReceiptScreen) => {
    class BillScreen extends ReceiptScreen {
        confirm() {
            this.props.resolve({ confirmed: true, payload: null });
            this.trigger("close-temp-screen");
        }
        whenClosing() {
            this.confirm();
        }
        /**
         * @override
         */
        async printReceipt() {
            await super.printReceipt();
            this.currentOrder._printed = false;
            if (this.env.pos.config.iface_print_skip_screen) {
                this.confirm();
            }
        }
>>>>>>> 8dbfd93303f (temp)
    }
    whenClosing() {
        this.confirm();
    }
    /**
     * @override
     */
    async printReceipt() {
        await super.printReceipt();
        this.currentOrder._printed = false;
    }
}

registry.category("pos_screens").add("BillScreen", BillScreen);
