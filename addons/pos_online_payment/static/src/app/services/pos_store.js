import { patch } from "@web/core/utils/patch";
import { CONSOLE_COLOR, PosStore } from "@point_of_sale/app/services/pos_store";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("ONLINE_PAYMENTS_NOTIFICATION", async ({ id }) => {
            // The bus communication is only protected by the name of the channel.
            // Therefore, no sensitive information is sent through it, only a
            // notification to invite the local browser to do a safe RPC to
            // the server to check the new state of the order.
            if (this.getOrder()?.id === id) {
                this.updateOnlinePaymentsDataWithServer(this.getOrder(), false);
            }
        });
    },
    async updateOnlinePaymentsDataWithServer(order, next_online_payment_amount) {
        if (!order.id) {
            return false;
        }
        try {
            const opData = await this.data.call("pos.order", "get_and_set_online_payments_data", [
                order.id,
                next_online_payment_amount,
            ]);
            return this.processOnlinePaymentsDataFromServer(order, opData);
        } catch (ex) {
            logPosMessage(
                "Store",
                "updateOnlinePaymentsDataWithServer",
                "Error while updating online payments data",
                CONSOLE_COLOR,
                [ex]
            );
            return null;
        }
    },
    processOnlinePaymentsDataFromServer(order, opData) {
        if (!opData) {
            return false;
        }
        if (opData.id !== order.id) {
            logPosMessage(
                "Store",
                "processOnlinePaymentsDataFromServer",
                "Called processOnlinePaymentsDataFromServer on the wrong order.",
                CONSOLE_COLOR
            );
        }
        if ("paid_order" in opData) {
            opData.isPaid = true;
            // only one line will have the `online_payment_resolver` method
            order.payment_ids.forEach((line) => line.onlinePaymentResolver?.(true));
            return opData;
        } else {
            opData.isPaid = false;
        }

        if (opData["deleted"] === true) {
            const onlinePm = order.payment_ids.filter(
                (line) => line.payment_method_id.is_online_payment
            );

            for (const line of onlinePm) {
                line.delete();
            }

            return opData;
        }

        let newDoneOnlinePayment = false;

        const opLinesToUpdate = order.payment_ids.filter(
            (line) =>
                line.payment_method_id.is_online_payment &&
                ["waiting", "done"].includes(line.getPaymentStatus())
        );
        for (const op of opData.online_payments) {
            const matchingLineIndex = opLinesToUpdate.findIndex(
                (pl) =>
                    pl.payment_method_id.id === op.payment_method_id &&
                    this.currency.isZero(pl.amount - op.amount)
            );
            let opLine = null;
            if (matchingLineIndex > -1) {
                opLine = opLinesToUpdate[matchingLineIndex];

                opLinesToUpdate.splice(matchingLineIndex, 1);
            }
            if (!opLine) {
                opLine = this.models["pos.payment"].create({
                    pos_order_id: order,
                    payment_method_id: op.payment_method_id,
                    amount: op.amount,
                });
                opData["modified_payment_lines"] = true;
            }
            opLine.setAmount(op.amount);
            opLine.can_be_reversed = false;
            if (opLine.getPaymentStatus() !== "done") {
                newDoneOnlinePayment = true;
            }
            opLine.setPaymentStatus("done");
        }
        for (const missingInServerLine of opLinesToUpdate) {
            if (missingInServerLine.getPaymentStatus() === "done") {
                this.paymentlines = order.payment_ids.filter(
                    (l) => l.uuid !== missingInServerLine.uuid
                );

                opData["modified_payment_lines"] = true;
            }
        }
        if (newDoneOnlinePayment || opData["modified_payment_lines"]) {
            // only one line will have the `online_payment_resolver` method
            order.payment_ids.forEach((line) => line.onlinePaymentResolver?.());
        }

        return opData;
    },
});
