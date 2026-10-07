import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },

    getPaymentActionState(line) {
        const state = super.getPaymentActionState(...arguments);
        if (line.isBancontactRefund && line.isBancontactRefundPending) {
            state.actions = [
                {
                    id: "check_status",
                    label: _t("Check status"),
                    title: _t("Check Refund Status"),
                    action: () => this.checkBancontactRefundStatus(line),
                    severity: "primary",
                },
                ...state.actions,
            ];
        }
        return state;
    },

    async checkBancontactRefundStatus(line) {
        await line.payment_interface.checkRefundStatus([line]);
        if (line.payment_status === "done") {
            await this.pos.autoValidateOrder();
        } else if (!line.payment_status) {
            this.notification.add(_t("The refund failed."), { type: "danger" });
        } else {
            this.notification.add(_t("The refund is still pending."), { type: "info" });
        }
    },
});
