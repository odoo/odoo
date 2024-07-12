import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { _t } from "@web/core/l10n/translation";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config.module_pos_sms) {
            this.state.input ||= this.currentOrder.get_partner()?.mobile || "";
        }
    },
    isValidPhoneNumber(x) {
        return x && /^\+?[()\d\s-.]{8,18}$/.test(x);
    },
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
        this.state.input = this.currentOrder.partner_id?.phone || this.state.input || "";
    },
    get isValidInput() {
        return this.state.mode === "phone"
            ? this.isValidPhoneNumber(this.state.input)
            : super.isValidInput;
    },
});
