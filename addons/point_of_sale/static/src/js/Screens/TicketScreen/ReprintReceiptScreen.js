/** @odoo-module */

import AbstractReceiptScreen from "@point_of_sale/js/Misc/AbstractReceiptScreen";
import Registries from "@point_of_sale/js/Registries";

const ReprintReceiptScreen = (AbstractReceiptScreen) => {
    class ReprintReceiptScreen extends AbstractReceiptScreen {
        setup() {
            super.setup();
            owl.onMounted(this.onMounted);
        }
        onMounted() {
            setTimeout(() => {
                this.printReceipt();
            }, 50);
        }
        confirm() {
            this.showScreen("TicketScreen", { reuseSavedUIState: true });
        }
        async printReceipt() {
            if (this.env.proxy.printer && this.env.pos.config.iface_print_skip_screen) {
                const result = await this._printReceipt();
                if (result) {
                    this.showScreen("TicketScreen", { reuseSavedUIState: true });
                }
            }
        }
        async tryReprint() {
            await this._printReceipt();
        }
    }
    ReprintReceiptScreen.template = "ReprintReceiptScreen";
    return ReprintReceiptScreen;
};
Registries.Component.addByExtending(ReprintReceiptScreen, AbstractReceiptScreen);

export default ReprintReceiptScreen;
