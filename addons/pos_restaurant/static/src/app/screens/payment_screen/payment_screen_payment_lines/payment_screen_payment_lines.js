import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreenPaymentLines.prototype, {
    async sendPaymentAdjust(line) {
        const amountDiff = line.pos_order_id.getTotalWithTax() - line.pos_order_id.getTotalPaid();
        await line.adjustAmount(amountDiff);
    },

    getPaymentActionState(line) {
        const state = super.getPaymentActionState(line);

        if (
            state?.id === "done" &&
            line.canBeAdjusted() &&
            line.pos_order_id.amountPaid < line.pos_order_id.priceIncl
        ) {
            state.actions.push({
                id: "adjust_amount",
                label: _t("Adjust Amount"),
                action: () => this.props.sendPaymentAdjust(line),
                severity: "warning",
            });
        }

        return state;
    },
});
