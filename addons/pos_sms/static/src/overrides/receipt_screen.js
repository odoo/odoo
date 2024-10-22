import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
    },
    showPhoneInput() {
        return super.showPhoneInput() || this.pos.config.module_pos_sms;
    },
<<<<<<< 18.0
    actionSendReceiptOnSMS() {
        this.sendReceipt.call({
            action: "action_sent_message_on_sms",
            destination: this.state.phone,
            name: "SMS",
        });
||||||| 7692c830bf453cd31f0520313c64da97e9c1d88a
    actionSendReceipt() {
        if (this.state.mode === "phone" && this.isValidPhoneNumber(this.state.input)) {
            this.sendReceipt.call({ action: "action_sent_message_on_sms", name: "SMS" });
        } else if (this.state.mode === "phone") {
            this.notification.add(_t("Please enter a valid phone number"), {
                type: "danger",
            });
        } else {
            super.actionSendReceipt(...arguments);
        }
    },
    changeMode(mode) {
        if (mode !== "phone" || !this.pos.config.module_pos_sms) {
            return super.changeMode(mode);
        }

        this.state.mode = mode;
        this.state.input = this.currentOrder.partner_id?.phone || "";
    },
    get isValidInput() {
        return this.state.mode === "phone"
            ? this.isValidPhoneNumber(this.state.input)
            : super.isValidInput;
=======
    actionSendReceipt() {
        if (this.state.mode === "phone" && this.isValidPhoneNumber(this.state.input)) {
            this.sendReceipt.call({ action: "action_sent_message_on_sms", name: "SMS" });
        } else if (this.state.mode === "phone") {
            this.notification.add(_t("Please enter a valid phone number"), {
                type: "danger",
            });
        } else {
            super.actionSendReceipt(...arguments);
        }
    },
    changeMode(mode) {
        if (mode !== "phone" || !this.pos.config.module_pos_sms) {
            return super.changeMode(mode);
        }

        this.state.mode = mode;
        this.state.input = this.currentOrder.partner_id?.mobile || "";
    },
    get isValidInput() {
        return this.state.mode === "phone"
            ? this.isValidPhoneNumber(this.state.input)
            : super.isValidInput;
>>>>>>> 0658ceeb111cae8fdc9aa1c4053ac0e46d1a6e42
    },
});
