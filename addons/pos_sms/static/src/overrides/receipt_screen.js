import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { _t } from "@web/core/l10n/translation";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
    },
    actionSendReceiptOnSMS() {
        if (this.isValidPhoneNumber(this.state.phone)) {
            this.sendReceipt.call({
                action: "action_sent_message_on_sms",
                destination: this.state.phone,
            });
        } else {
            this.notification.add(_t("Please enter a valid phone number"), {
                type: "danger",
            });
        }
    },
});
