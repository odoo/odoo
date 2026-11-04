import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { floatIsZero } from "@web/core/utils/numbers";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("ONLINE_PAYMENTS_NOTIFICATION", ({ id }) => {
            // The bus communication is only protected by the name of the channel.
            // Therefore, no sensitive information is sent through it, only a
            // notification to invite the local browser to do a safe RPC to
            // the server to check the new state of the order.
            if (this.get_order()?.id === id) {
                this.update_online_payments_data_with_server(this.get_order(), false);
            }
        });
    },
    async update_online_payments_data_with_server(order, next_online_payment_amount) {
        if (!order.id) {
            return false;
        }
        try {
            const opData = await this.data.call("pos.order", "get_and_set_online_payments_data", [
                order.id,
                next_online_payment_amount,
            ]);
            return this.process_online_payments_data_from_server(order, opData);
        } catch (ex) {
            console.error("update_online_payments_data_with_server failed: ", ex);
            return null;
        }
    },
    process_online_payments_data_from_server(order, opData) {
        if (!opData) {
            return false;
        }
        if (opData.id !== order.id) {
            console.error("Called process_online_payments_data_from_server on the wrong order.");
        }
        if ("paid_order" in opData) {
            opData.is_paid = true;
            // only one line will have the `online_payment_resolver` method
            order.payment_ids.forEach((line) => line.onlinePaymentResolver?.(true));
            return opData;
        } else {
            opData.is_paid = false;
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
                ["waiting", "done"].includes(line.get_payment_status())
        );
        for (const op of opData.online_payments) {
            const matchingLineIndex = opLinesToUpdate.findIndex(
                (pl) =>
                    pl.payment_method_id.id === op.payment_method_id &&
                    floatIsZero(pl.amount - op.amount, this.currency.decimal_places)
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
            opLine.set_amount(op.amount);
            opLine.can_be_reversed = false;
            if (opLine.get_payment_status() !== "done") {
                newDoneOnlinePayment = true;
            }
            opLine.set_payment_status("done");
        }
        for (const missingInServerLine of opLinesToUpdate) {
            if (missingInServerLine.get_payment_status() === "done") {
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
