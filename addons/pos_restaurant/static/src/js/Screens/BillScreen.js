/** @odoo-module */

import ReceiptScreen from "@point_of_sale/js/Screens/ReceiptScreen/ReceiptScreen";
import Registries from "@point_of_sale/js/Registries";

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
    }
    BillScreen.template = "BillScreen";
    return BillScreen;
};

Registries.Component.addByExtending(BillScreen, ReceiptScreen);

export default BillScreen;
