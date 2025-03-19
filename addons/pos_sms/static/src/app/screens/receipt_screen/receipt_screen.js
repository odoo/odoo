import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    showPhoneInput() {
        return super.showPhoneInput() || this.pos.config.module_pos_sms;
    },
    actionSendReceiptOnSMS() {
        this.sendReceipt.call({
            action: "action_sent_message_on_sms",
            destination: this.state.phone,
            name: "SMS",
        });
    },
});
