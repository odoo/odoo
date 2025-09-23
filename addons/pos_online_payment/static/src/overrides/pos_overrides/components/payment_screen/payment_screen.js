import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { OnlinePaymentPopup } from "@pos_online_payment/app/online_payment_popup/online_payment_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { qrCodeSrc } from "@point_of_sale/utils";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.is_online_payment && typeof this.currentOrder.id === "string") {
            this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
            this.pos.addPendingOrder([this.currentOrder.id]);
            await this.pos.syncAllOrders();
        }
        return await super.addNewPaymentLine(...arguments);
    },
    getRemainingOnlinePaymentLines() {
        return this.paymentLines.filter(
            (line) =>
                line.payment_method_id.is_online_payment && line.get_payment_status() !== "done"
        );
    },
    checkRemainingOnlinePaymentLines(unpaidAmount) {
        const remainingLines = this.getRemainingOnlinePaymentLines();
        let remainingAmount = 0;
        let amount = 0;
        for (const line of remainingLines) {
            amount = line.get_amount();
            if (amount <= 0) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invalid online payment"),
                    body: _t(
                        "Online payments cannot have a negative amount (%s: %s).",
                        line.payment_method_id.name,
                        this.env.utils.formatCurrency(amount)
                    ),
                });
                return false;
            }
            remainingAmount += amount;
        }
        if (!this.env.utils.floatIsZero(unpaidAmount - remainingAmount)) {
            this.dialog.add(AlertDialog, {
                title: _t("Invalid online payments"),
                body: _t(
                    "The total amount of remaining online payments to execute (%s) doesn't correspond to the remaining unpaid amount of the order (%s).",
                    this.env.utils.formatCurrency(remainingAmount),
                    this.env.utils.formatCurrency(unpaidAmount)
                ),
            });
            return false;
        }
        return true;
    },
    //@override
    async _isOrderValid(isForceValidate) {
        if (!(await super._isOrderValid(...arguments))) {
            return false;
        }

        if (!this.payment_methods_from_config.some((pm) => pm.is_online_payment)) {
            return true;
        }

        if (this.currentOrder.finalized) {
            this.afterOrderValidation(false);
            return false;
        }

        const onlinePaymentLines = this.getRemainingOnlinePaymentLines();
        if (onlinePaymentLines.length > 0) {
            if (!this.currentOrder.id) {
                this.cancelOnlinePayment(this.currentOrder);
                this.dialog.add(AlertDialog, {
                    title: _t("Online payment unavailable"),
                    body: _t("The QR Code for paying could not be generated."),
                });
                return false;
            }
            let prevOnlinePaymentLine = null;
            let lastOrderServerOPData = null;
            for (const onlinePaymentLine of onlinePaymentLines) {
                const onlinePaymentLineAmount = onlinePaymentLine.get_amount();
                // The local state is not aware if the online payment has already been done.
                lastOrderServerOPData = await this.pos.update_online_payments_data_with_server(
                    this.currentOrder,
                    onlinePaymentLineAmount
                );
                if (!lastOrderServerOPData) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Online payment unavailable"),
                        body: _t(
                            "There is a problem with the server. The order online payment status cannot be retrieved."
                        ),
                    });
                    return false;
                }
                if (!lastOrderServerOPData.is_paid) {
                    if (lastOrderServerOPData.modified_payment_lines) {
                        this.cancelOnlinePayment(this.currentOrder);
                        this.dialog.add(AlertDialog, {
                            title: _t("Updated online payments"),
                            body: _t("There are online payments that were missing in your view."),
                        });
                        return false;
                    }
                    if (
                        (prevOnlinePaymentLine &&
                            prevOnlinePaymentLine?.get_payment_status() !== "done") ||
                        !this.checkRemainingOnlinePaymentLines(lastOrderServerOPData.amount_unpaid)
                    ) {
                        this.cancelOnlinePayment(this.currentOrder);
                        return false;
                    }

                    onlinePaymentLine.set_payment_status("waiting");
                    this.currentOrder.select_paymentline(onlinePaymentLine);
                    const onlinePaymentData = {
                        formattedAmount: this.env.utils.formatCurrency(onlinePaymentLineAmount),
                        qrCode: qrCodeSrc(
                            `${this.pos.session._base_url}/pos/pay/${this.currentOrder.id}?access_token=${this.currentOrder.access_token}`
                        ),
                        orderName: this.currentOrder.name,
                    };
                    this.currentOrder.onlinePaymentData = onlinePaymentData;
                    const qrCodePopupCloser = this.dialog.add(
                        OnlinePaymentPopup,
                        onlinePaymentData,
                        {
                            onClose: () => {
                                onlinePaymentLine.onlinePaymentResolver(false);
                            },
                        }
                    );
                    const paymentResult = await new Promise(
                        (r) => (onlinePaymentLine.onlinePaymentResolver = r)
                    );
                    if (!paymentResult) {
                        this.cancelOnlinePayment(this.currentOrder);
                        onlinePaymentLine.set_payment_status(undefined);
                        return false;
                    }
                    qrCodePopupCloser();
                    if (onlinePaymentLine.get_payment_status() === "waiting") {
                        onlinePaymentLine.set_payment_status(undefined);
                    }
                    prevOnlinePaymentLine = onlinePaymentLine;
                }
            }

            if (!lastOrderServerOPData || !lastOrderServerOPData.is_paid) {
                lastOrderServerOPData = await this.pos.update_online_payments_data_with_server(
                    this.currentOrder,
                    0
                );
            }
            if (!lastOrderServerOPData || !lastOrderServerOPData.is_paid) {
                return false;
            }

            await this.afterPaidOrderSavedOnServer(lastOrderServerOPData.paid_order);
            return false; // Cancel normal flow because the current order is already saved on the server.
        } else if (typeof this.currentOrder.id === "number") {
            const orderServerOPData = await this.pos.update_online_payments_data_with_server(
                this.currentOrder,
                0
            );
            if (!orderServerOPData) {
                return ask(this.dialog, {
                    title: _t("Online payment unavailable"),
                    body: _t(
                        "There is a problem with the server. The order online payment status cannot be retrieved. Are you sure there is no online payment for this order ?"
                    ),
                    confirmLabel: _t("Yes"),
                });
            }
            if (orderServerOPData.is_paid) {
                await this.afterPaidOrderSavedOnServer(orderServerOPData.paid_order);
                return false; // Cancel normal flow because the current order is already saved on the server.
            }
            if (orderServerOPData.modified_payment_lines) {
                this.dialog.add(AlertDialog, {
                    title: _t("Updated online payments"),
                    body: _t("There are online payments that were missing in your view."),
                });
                return false;
            }
        }

        return true;
    },
    cancelOnlinePayment(order) {
        // Remove the draft order from the server if there is no done online payment
        this.pos.update_online_payments_data_with_server(order, 0);
    },
    async afterPaidOrderSavedOnServer(orderJSON) {
        if (!orderJSON) {
            this.dialog.add(AlertDialog, {
                title: _t("Server error"),
                body: _t("The saved order could not be retrieved."),
            });
            return;
        }

        // Update the local order with the data from the server, because it's the server
        // that is responsible for saving the final state of an order when there is an
        // online payment in it.
        // This prevents the case where the cashier changes the payment lines after the
        // order is paid with an online payment and the server saves the order as paid.
        // Without that update, the payment lines printed on the receipt ticket would
        // be invalid.
        const isInvoiceRequested = this.currentOrder.is_to_invoice();
        if (!orderJSON[0] || this.currentOrder.id !== orderJSON[0].id) {
            this.dialog.add(AlertDialog, {
                title: _t("Order saving issue"),
                body: _t("The order has not been saved correctly on the server."),
            });
            return;
        }
        this.currentOrder.state = "paid";
        this.pos.validated_orders_name_server_id_map[this.currentOrder.name] = this.currentOrder.id;

        // Now, do practically the normal flow
        if (
            (this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) &&
            this.pos.config.iface_cashdrawer
        ) {
            this.hardwareProxy.printer.openCashbox();
        }

        if (isInvoiceRequested) {
            if (!orderJSON[0].raw.account_move) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invoice could not be generated"),
                    body: _t("The invoice could not be generated."),
                });
            } else {
                await this.invoiceService.downloadPdf(orderJSON[0].raw.account_move);
            }
        }

        await this.postPushOrderResolve([this.currentOrder.id]);

        this.afterOrderValidation(true);
    },
});
