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
            const [order] = await this.data.loadServerOrders([["id", "=", id]]);
            if (!order) {
                return;
            }
            for (const line of order.payment_ids) {
                if (line.payment_method_id.type === "online") {
                    line.payment_interface?.checkPaymentStatus(line);
                }
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
            return await this.processOnlinePaymentsDataFromServer(order, opData);
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
    async processOnlinePaymentsDataFromServer(order, opData) {
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

        opData.isPaid = "paid_order" in opData;
        if (opData.isPaid) {
            return opData;
        }

        // The server writes the online payments on the lines saved by the POS,
        // a line unknown or not done here was paid without this POS knowing it.
        const doneLineIds = new Set(
            order.payment_ids
                .filter((line) => line.payment_status === "done")
                .map((line) => line.id)
        );
        if (opData.online_payments.some((op) => !doneLineIds.has(op.id))) {
            await this.data.loadServerOrders([["id", "=", order.id]]);
            opData.modified_payment_lines = true;
        }
        return opData;
    },
});
