import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
    },
    showPhoneInput() {
        return super.showPhoneInput() || this.pos.config.whatsapp_enabled;
    },
    actionSendReceiptOnWhatsapp() {
        this.sendReceipt.call({
            action: "action_sent_receipt_on_whatsapp",
            destination: this.state.phone,
            name: "WhatsApp",
        });
    },
});
