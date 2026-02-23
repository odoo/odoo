import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { OnlinePaymentPopup } from "@pos_online_payment/app/components/popups/online_payment_popup/online_payment_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { qrCodeSrc } from "@point_of_sale/utils";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(OrderPaymentValidation.prototype, {
    getRemainingOnlinePaymentLines() {
        return this.paymentLines.filter(
            (line) => line.payment_method_id.is_online_payment && line.getPaymentStatus() !== "done"
        );
    },
    checkRemainingOnlinePaymentLines(unpaidAmount) {
        const remainingLines = this.getRemainingOnlinePaymentLines();
        let remainingAmount = 0;
        let amount = 0;
        for (const line of remainingLines) {
            amount = line.getAmount();
            if (amount <= 0) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Invalid online payment"),
                    body: _t(
                        "Online payments cannot have a negative amount (%s: %s).",
                        line.payment_method_id.name,
                        this.pos.env.utils.formatCurrency(amount)
                    ),
                });
                return false;
            }
            remainingAmount += amount;
        }
        if (!this.pos.currency.isZero(unpaidAmount - remainingAmount)) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Invalid online payments"),
                body: _t(
                    "The total amount of remaining online payments to execute (%s) doesn't correspond to the remaining unpaid amount of the order (%s).",
                    this.pos.env.utils.formatCurrency(remainingAmount),
                    this.pos.env.utils.formatCurrency(unpaidAmount)
                ),
            });
            return false;
        }
        return true;
    },
    //@override
    async isOrderValid(isForceValidate) {
        if (!(await super.isOrderValid(...arguments))) {
            return false;
        }

        if (!this.payment_methods_from_config.some((pm) => pm.is_online_payment)) {
            return true;
        }

        if (this.order.finalized) {
            this.afterOrderValidation(false);
            return false;
        }

        const onlinePaymentLines = this.getRemainingOnlinePaymentLines();
        if (onlinePaymentLines.length > 0) {
            if (!this.order.id) {
                this.cancelOnlinePayment(this.order);
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Online payment unavailable"),
                    body: _t("The QR Code for paying could not be generated."),
                });
                return false;
            }
            let prevOnlinePaymentLine = null;
            let lastOrderServerOPData = null;
            for (const onlinePaymentLine of onlinePaymentLines) {
                const onlinePaymentLineAmount = onlinePaymentLine.getAmount();
                // The local state is not aware if the online payment has already been done.
                lastOrderServerOPData = await this.pos.updateOnlinePaymentsDataWithServer(
                    this.order,
                    onlinePaymentLineAmount
                );
                if (!lastOrderServerOPData) {
                    this.pos.dialog.add(AlertDialog, {
                        title: _t("Online payment unavailable"),
                        body: _t(
                            "There is a problem with the server. The order online payment status cannot be retrieved."
                        ),
                        showReloadButton: true,
                    });
                    return false;
                }
                if (!lastOrderServerOPData.isPaid) {
                    if (lastOrderServerOPData.modified_payment_lines) {
                        this.cancelOnlinePayment(this.order);
                        this.pos.dialog.add(AlertDialog, {
                            title: _t("Updated online payments"),
                            body: _t("There are online payments that were missing in your view."),
                        });
                        return false;
                    }
                    if (
                        (prevOnlinePaymentLine &&
                            prevOnlinePaymentLine?.getPaymentStatus() !== "done") ||
                        !this.checkRemainingOnlinePaymentLines(lastOrderServerOPData.amount_unpaid)
                    ) {
                        this.cancelOnlinePayment(this.order);
                        return false;
                    }

                    await this.pos.syncAllOrders({ orders: [this.order] });
                    onlinePaymentLine.setPaymentStatus("waiting");
                    this.order.selectPaymentline(onlinePaymentLine);
                    const onlinePaymentData = {
                        formattedAmount: this.pos.env.utils.formatCurrency(onlinePaymentLineAmount),
                        qrCode: qrCodeSrc(
                            `${this.pos.config._base_url}/pos/pay/${this.order.id}?access_token=${this.order.access_token}`
                        ),
                        orderName: this.order.name,
                    };
                    this.order.onlinePaymentData = onlinePaymentData;
                    const qrCodePopupCloser = this.pos.dialog.add(
                        OnlinePaymentPopup,
                        onlinePaymentData,
                        {
                            onClose: () => {
                                onlinePaymentLine.onlinePaymentResolver(false);
                                this.currentOrder.onlinePaymentData = {};
                            },
                        }
                    );
                    const paymentResult = await new Promise(
                        (r) => (onlinePaymentLine.onlinePaymentResolver = r)
                    );
                    if (!paymentResult) {
                        this.cancelOnlinePayment(this.order);
                        onlinePaymentLine.setPaymentStatus(undefined);
                        return false;
                    }
                    qrCodePopupCloser();
                    if (onlinePaymentLine.getPaymentStatus() === "waiting") {
                        onlinePaymentLine.setPaymentStatus(undefined);
                    }
                    prevOnlinePaymentLine = onlinePaymentLine;
                }
            }

            if (!lastOrderServerOPData || !lastOrderServerOPData.isPaid) {
                lastOrderServerOPData = await this.pos.updateOnlinePaymentsDataWithServer(
                    this.order,
                    0
                );
            }
            if (!lastOrderServerOPData || !lastOrderServerOPData.isPaid) {
                return false;
            }

            await this.afterPaidOrderSavedOnServer(lastOrderServerOPData.paid_order);
            return false; // Cancel normal flow because the current order is already saved on the server.
        } else if (this.order.isSynced) {
            const orderServerOPData = await this.pos.updateOnlinePaymentsDataWithServer(
                this.order,
                0
            );
            if (!orderServerOPData) {
                return ask(this.pos.dialog, {
                    title: _t("Online payment unavailable"),
                    body: _t(
                        "There is a problem with the server. The order online payment status cannot be retrieved. Are you sure there is no online payment for this order ?"
                    ),
                    confirmLabel: _t("Yes"),
                });
            }
            if (orderServerOPData.isPaid) {
                await this.afterPaidOrderSavedOnServer(orderServerOPData.paid_order);
                return false; // Cancel normal flow because the current order is already saved on the server.
            }
            if (orderServerOPData.modified_payment_lines) {
                this.pos.dialog.add(AlertDialog, {
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
        this.pos.updateOnlinePaymentsDataWithServer(order, 0);
    },
    async afterPaidOrderSavedOnServer(orderJSON) {
        if (!orderJSON) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Server error"),
                body: _t("The saved order could not be retrieved."),
                showReloadButton: true,
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
        const isInvoiceRequested = this.order.isToInvoice();
        if (!orderJSON[0] || this.order.id !== orderJSON[0].id) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Order saving issue"),
                body: _t("The order has not been saved correctly on the server."),
                showReloadButton: true,
            });
            return;
        }
        this.order.state = "paid";
        this.pos.validated_orders_name_server_id_map[this.order.name] = this.order.id;

        // Now, do practically the normal flow
        if (
            (this.order.isPaidWithCash() || this.order.change) &&
            this.pos.config.iface_cashdrawer
        ) {
            this.pos.hardwareProxy.openCashbox();
        }

        if (isInvoiceRequested) {
            if (!orderJSON[0].account_move) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Invoice could not be generated"),
                    body: _t("The invoice could not be generated."),
                    showReloadButton: true,
                });
            } else {
                await this.pos.env.services.account_move.downloadPdf(orderJSON[0].account_move);
            }
        }

        await this.postPushOrderResolve([this.order.id]);

        await this.afterOrderValidation(true);
        const nextPage = this.nextPage;
        this.pos.navigate(nextPage.page, nextPage.params);
    },
});
