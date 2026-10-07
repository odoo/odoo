import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines.prototype, {
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

    canDeleteLine(line) {
        return super.canDeleteLine(...arguments) && !line.isBancontactRefundPending;
    },

    async checkBancontactRefundStatus(line) {
        await line.payment_interface.checkRefundStatus([line]);
        await this.pos.handleBancontactRefundStatus(line);
    },
});
