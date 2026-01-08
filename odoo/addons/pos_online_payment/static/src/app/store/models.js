/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Order, Payment } from "@point_of_sale/app/store/models";
import { floatIsZero } from "@web/core/utils/numbers";

patch(Order.prototype, {
    async update_online_payments_data_with_server(orm, next_online_payment_amount) {
        if (!this.server_id) {
            return false;
        }
        try {
            const opData = await orm.call("pos.order", "get_and_set_online_payments_data", [this.server_id, next_online_payment_amount]);
            return this.process_online_payments_data_from_server(opData);
        } catch (ex) {
            console.error("update_online_payments_data_with_server failed: ", ex);
            return null;
        }
    },
    async process_online_payments_data_from_server(opData) {
        if (!opData) {
            return false;
        }
        if (opData.id !== this.server_id) {
            console.error("Called process_online_payments_data_from_server on the wrong order.");
        }

        if ("paid_order" in opData) {
            opData.is_paid = true;
            this.uiState.PaymentScreen?.onlinePaymentPopup?.setReceivedOrderServerOPData(opData);
            return opData;
        } else {
            opData.is_paid = false;
        }

        if ("deleted" in opData && opData["deleted"]) {
            // The current order was previously saved on the server in the draft state, and has been deleted.
            this.server_id = false;
        }

        let newDoneOnlinePayment = false;

        const opLinesToUpdate = this.paymentlines.filter(
            (line) => line.payment_method.is_online_payment && ["waiting", "done"].includes(line.get_payment_status())
        );
        for (const op of opData.online_payments) {
            const matchingLineIndex = opLinesToUpdate.findIndex(
                (pl) => pl.payment_method.id === op.payment_method_id && floatIsZero(pl.amount - op.amount, this.pos.currency.decimal_places)
            );
            let opLine = null;
            if (matchingLineIndex > -1) {
                opLine = opLinesToUpdate[matchingLineIndex];

                opLinesToUpdate.splice(matchingLineIndex, 1);
            }
            if (!opLine) {
                opLine = new Payment(
                    {},
                    {
                        order: this,
                        payment_method: this.pos.payment_methods_by_id[op.payment_method_id],
                        pos: this.pos,
                    }
                );
                this.paymentlines.add(opLine);
                opData['modified_payment_lines'] = true;
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
                this.paymentlines.remove(missingInServerLine);
                opData['modified_payment_lines'] = true;
            }
        }
        if (newDoneOnlinePayment || opData['modified_payment_lines']) {
            this.uiState.PaymentScreen?.onlinePaymentPopup?.cancel();
        }

        return opData;
    },
});

patch(Payment.prototype, {
    //@override
    export_as_JSON() {
        if (this.payment_method.is_online_payment) {
            return null; // It is the role of the server to save the online payment, not the role of the POS session.
        } else {
            return super.export_as_JSON();
        }
    },
    //@override
    canBeAdjusted() {
        if (this.payment_method.is_online_payment) {
            return false;
        } else {
            return super.canBeAdjusted();
        }
    },
});
