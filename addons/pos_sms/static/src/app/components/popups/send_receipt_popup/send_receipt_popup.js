import { patch } from "@web/core/utils/patch";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";

patch(SendReceiptPopup.prototype, {
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
    get sendList() {
        const list = super.sendList;
        if (this.pos.config.module_pos_sms) {
            list.find((item) => item.model === "phone").buttons.push({
                click: () => this.actionSendReceiptOnSMS(),
                status: this.sendReceipt.lastArgs?.[0]?.name == "SMS" && this.sendReceipt.status,
                icon: "fa-lg fa-mobile",
                disabled: () => !this.isValidPhone,
            });
        }
        return list;
    },
});
