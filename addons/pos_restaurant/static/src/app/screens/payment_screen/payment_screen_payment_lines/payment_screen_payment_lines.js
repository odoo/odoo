import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreenPaymentLines.prototype, {
    async sendPaymentAdjust(line) {
        const prevAmount = line.getAmount();
        const amountDiff = line.pos_order_id.getTotalWithTax() - line.pos_order_id.getTotalPaid();
        const newAmount = prevAmount + amountDiff;

        line.setAmount(newAmount);
        line.setPaymentStatus("waiting");

        const isAdjustSuccessful =
            await line.payment_method_id.payment_interface?.sendPaymentAdjust(line.uuid);

        if (!isAdjustSuccessful) {
            line.setAmount(prevAmount);
        }

        line.setPaymentStatus("done");
    },

    getPaymentActionState(line) {
        const state = super.getPaymentActionState(line);

        if (
            (state.id === "paid" || state.id === "refunded") &&
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
