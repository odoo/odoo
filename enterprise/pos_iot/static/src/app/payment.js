import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentIngenico extends PaymentInterface {
    get_terminal() {
        return this.payment_method_id.terminal_proxy;
    }

    send_payment_request(uuid) {
        var self = this;
        super.send_payment_request(...arguments);
        const terminal_proxy = self.get_terminal();

        if (!terminal_proxy) {
            this._showErrorConfig();
            return Promise.resolve(false);
        }

        return new Promise(function (resolve) {
            self._waitingResponse = self._waitingPayment;
            terminal_proxy.addListener(
                self._onValueChange.bind(self, resolve, self.pos.get_order())
            );
            self._send_request(self.get_payment_data(uuid));
        });
    }

    get_payment_data(uuid) {
        const paymentline = this.pos.get_order().get_paymentline_by_uuid(uuid);
        return {
            messageType: "Transaction",
            // The last 13 characters of the uuid is a 52-bit integer, fits in the Number data type.
            // Use it as the TransactionID.
            TransactionID: parseInt(uuid.replace(/-/g, "").slice(19, 32), 16),
            cid: uuid,
            amount: Math.round(paymentline.amount * 100),
        };
    }

    send_payment_cancel(order, uuid) {
        var self = this;
        var terminal = this.get_terminal();
        if (terminal) {
            super.send_payment_cancel(...arguments);
            var data = {
                messageType: "Cancel",
                reason: "manual",
            };
            return new Promise(function (resolve) {
                self._waitingResponse = self._waitingCancel;
                terminal.addListener(self._onValueChange.bind(self, resolve, order));
                self._send_request(data);
            });
        }
        return Promise.reject();
    }

    // extra private methods
    _send_request(data) {
        var self = this;
        this.get_terminal()
            .action(data)
            .then(self._onActionResult.bind(self))
            .catch((e) => {
                self._onActionFail();
            });
    }
    _onActionResult(data) {
        if (data.result === false) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Connection to terminal failed"),
                body: _t("Please check if the terminal is still connected."),
            });
            if (this.pos.get_order().get_selected_paymentline()) {
                this.pos.get_order().get_selected_paymentline().set_payment_status("force_done");
            }
        }
    }
    _onActionFail() {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Connection to IoT Box failed"),
            body: _t("Please check if the IoT Box is still connected."),
        });
        if (this.pos.get_order().get_selected_paymentline()) {
            this.pos.get_order().get_selected_paymentline().set_payment_status("force_done");
        }
    }
    _showErrorConfig() {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Configuration of payment terminal failed"),
            body: _t("You must select a payment terminal in your POS config."),
        });
    }

    _waitingPayment(resolve, data, line) {
        if (data.Error) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Payment terminal error"),
                body: _t(data.Error),
            });
            this.get_terminal().removeListener();
            resolve(false);
        } else if (data.Response === "Approved") {
            this.get_terminal().removeListener();
            resolve(true);
        } else if (["WaitingForCard", "WaitingForPin"].includes(data.Stage)) {
            line.set_payment_status("waitingCard");
        }
    }

    _waitingCancel(resolve, data) {
        if (data.Stage === "Finished" || data.Error) {
            this.get_terminal().removeListener();
            resolve(true);
        }
    }

    /**
     * Function ran when Device status changes.
     *
     * @param {Object} data.Response
     * @param {Object} data.Stage
     * @param {string} data.Ticket
     * @param {Object} data.device_id
     * @param {string} data.owner
     * @param {string} data.session_id
     * @param {Object} data.value
     * @param {string} data.Card
     * @param {string} data.cid
     * @param {Object} [data.result]
     */
    _onValueChange(resolve, order, data) {
        const result = data.result ? data.result : data; // compatibility v19.1+ iot box
        const line = order.get_paymentline_by_uuid(result.cid);
        if (line && line.payment_method_id.terminal_proxy) {
            this._waitingResponse(resolve, result, line);
            if (result.Ticket) {
                line.set_receipt_info(result.Ticket);
            }
            if (result.Card) {
                line.card_type = result.Card;
            }
        }
    }
}

export class PaymentWorldline extends PaymentIngenico {
    send_payment_cancel(order, uuid) {
        if (this.get_terminal()) {
            this._send_request({ messageType: "Cancel", cid: uuid });
        }

        return new Promise((resolve) => {
            this.cancel_resolve = resolve;
        });
    }

    send_payment_request(uuid) {
        const paymentline = this.pos.get_order().get_paymentline_by_uuid(uuid);
        paymentline.transaction_id = Math.floor(Math.random() * Math.pow(2, 32)); // 4 random bytes
        return super.send_payment_request(...arguments);
    }

    get_payment_data(uuid) {
        var data = super.get_payment_data(...arguments);
        data.actionIdentifier = this.pos.get_order().get_paymentline_by_uuid(uuid).transaction_id;
        return data;
    }

    _waitingPayment(resolve, data, line) {
        if (data.Stage == "Cancel") {
            // Result of a cancel request
            if (data.Error) {
                // Cancel failed, wait for transaction response
                this.cancel_resolve?.(false);
                line.set_payment_status("waitingCard");
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Transaction could not be cancelled"),
                    body: data.Error,
                });
            } else {
                this.get_terminal().removeListener();
                this.cancel_resolve?.(true);
                resolve(false);
            }
        } else if (data.Disconnected) {
            // Terminal disconnected
            line.set_payment_status("force_done");
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Terminal Disconnected"),
                body: _t(
                    "Please check the network connection and then check the status of the last transaction manually."
                ),
            });
        } else if (line.payment_status !== "retry") {
            // Result of a transaction
            return super._waitingPayment(...arguments);
        }
    }
}
