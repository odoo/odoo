import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreenPaymentLines.prototype, {
    async sendPaymentAdjust(line) {
        const adjustmentAmount = line.pos_order_id.remainingDue;
        line.setPaymentStatus("waiting");
        try {
            await line.adjustAmount(adjustmentAmount);
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t(
                    "%s payment adjustment failed",
                    this.adjustableTipLine.payment_method_id.name
                ),
                body: error?.data?.message ?? error?.message ?? error,
            });
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
                action: () => this.sendPaymentAdjust(line),
                severity: "warning",
            });
        }

        return state;
    },
});
