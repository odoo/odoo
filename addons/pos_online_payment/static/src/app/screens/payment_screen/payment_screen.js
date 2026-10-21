import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async deletePaymentLine(uuid) {
        const order = this.currentOrder;
        const line = this.paymentLines.find((line) => line.uuid === uuid);
        if (
            line.payment_method_id.type === "online" &&
            line.isSynced &&
            line.payment_status !== "done"
        ) {
            // The customer may have paid it while this POS missed the notification
            const opData = await this.pos.updateOnlinePaymentsDataWithServer(order, false);
            if (!opData) {
                this.dialog.add(AlertDialog, {
                    title: _t("Online payment unavailable"),
                    body: _t(
                        "Can't check whether this online payment was paid. Check the connection and try again."
                    ),
                });
                return;
            }
            if (opData.isPaid) {
                await this.pos.data.loadServerOrders([["id", "=", order.id]]);
            }
            if (this.paymentLines.find((line) => line.uuid === uuid)?.payment_status === "done") {
                this.dialog.add(AlertDialog, {
                    title: _t("Online payment already paid"),
                    body: _t(
                        "The customer has already paid this online payment, it can't be deleted."
                    ),
                });
                return;
            }
        }
        return super.deletePaymentLine(...arguments);
    },
});
