/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { OnlinePaymentPopup } from "@pos_online_payment/app/utils/online_payment_popup/online_payment_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { floatIsZero } from "@web/core/utils/numbers";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(PaymentScreen.prototype, {
    getRemainingOnlinePaymentLines() {
        return this.paymentLines.filter(
            (line) => line.payment_method.is_online_payment && line.get_payment_status() !== "done"
        );
    },
    checkRemainingOnlinePaymentLines(unpaidAmount) {
        const remainingLines = this.getRemainingOnlinePaymentLines();
        let remainingAmount = 0;
        let amount = 0;
        for (const line of remainingLines) {
            amount = line.get_amount();
            if (amount <= 0) {
                this.popup.add(ErrorPopup, {
                    title: _t("Invalid online payment"),
                    body: _t(
                        "Online payments cannot have a negative amount (%s: %s).",
                        line.payment_method.name,
                        this.env.utils.formatCurrency(amount)
                    ),
                });
                return false;
            }
            remainingAmount += amount;
        }
        if (!floatIsZero(unpaidAmount - remainingAmount, this.pos.currency.decimal_places)) {
            this.popup.add(ErrorPopup, {
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
        if (!await super._isOrderValid(...arguments)) {
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
            // Send the order to the server everytime before the online payments process to
            // allow the server to get the data for online payments and link the successful
            // online payments to the order.
            // The validation process will be done by the server directly after a successful
            // online payment that makes the order fully paid.
            this.currentOrder.date_order = luxon.DateTime.now();
            this.currentOrder.save_to_db();
            this.pos.addOrderToUpdateSet();

            try {
                await this.pos.sendDraftToServer();
            } catch (error) {
                // Code from _finalizeValidation():
                if (error.code == 700 || error.code == 701) {
                    this.error = true;
                }

                if ("code" in error) {
                    // We started putting `code` in the rejected object for invoicing error.
                    // We can continue with that convention such that when the error has `code`,
                    // then it is an error when invoicing. Besides, _handlePushOrderError was
                    // introduce to handle invoicing error logic.
                    await this._handlePushOrderError(error);
                }
                this.showSaveOrderOnServerErrorPopup();
                return false;
            }

            if (!this.currentOrder.server_id) {
                this.showSaveOrderOnServerErrorPopup();
                return false;
            }

            if (!this.currentOrder.server_id) {
                this.cancelOnlinePayment(this.currentOrder);
                this.popup.add(ErrorPopup, {
                    title: _t("Online payment unavailable"),
                    body: _t("The QR Code for paying could not be generated."),
                });
                return false;
            }
            const qrCodeImgSrc = qrCodeSrc(`${this.pos.base_url}/pos/pay/${this.currentOrder.server_id}?access_token=${this.currentOrder.access_token}`);

            let prevOnlinePaymentLine = null;
            let lastOrderServerOPData = null;
            for (const onlinePaymentLine of onlinePaymentLines) {
                const onlinePaymentLineAmount = onlinePaymentLine.get_amount();
                // The local state is not aware if the online payment has already been done.
                lastOrderServerOPData = await this.currentOrder.update_online_payments_data_with_server(this.pos.orm, onlinePaymentLineAmount);
                if (!lastOrderServerOPData) {
                    this.popup.add(ErrorPopup, {
                        title: _t("Online payment unavailable"),
                        body: _t("There is a problem with the server. The order online payment status cannot be retrieved."),
                    });
                    return false;
                }
                if (!lastOrderServerOPData.is_paid) {
                    if (lastOrderServerOPData.modified_payment_lines) {
                        this.cancelOnlinePayment(this.currentOrder);
                        this.showModifiedOnlinePaymentsPopup();
                        return false;
                    }
                    if ((prevOnlinePaymentLine && prevOnlinePaymentLine.get_payment_status() !== "done") || !this.checkRemainingOnlinePaymentLines(lastOrderServerOPData.amount_unpaid)) {
                        this.cancelOnlinePayment(this.currentOrder);
                        return false;
                    }

                    onlinePaymentLine.set_payment_status("waiting");
                    this.currentOrder.select_paymentline(onlinePaymentLine);
                    lastOrderServerOPData = await this.showOnlinePaymentQrCode(qrCodeImgSrc, onlinePaymentLineAmount);
                    if (onlinePaymentLine.get_payment_status() === "waiting") {
                        onlinePaymentLine.set_payment_status(undefined);
                    }
                    prevOnlinePaymentLine = onlinePaymentLine;
                }
            }

            if (!lastOrderServerOPData || !lastOrderServerOPData.is_paid) {
                lastOrderServerOPData = await this.currentOrder.update_online_payments_data_with_server(this.pos.orm, 0);
            }
            if (!lastOrderServerOPData || !lastOrderServerOPData.is_paid) {
                return false;
            }

            await this.afterPaidOrderSavedOnServer(lastOrderServerOPData.paid_order);
            return false; // Cancel normal flow because the current order is already saved on the server.
        } else if (this.currentOrder.server_id) {
            const orderServerOPData = await this.currentOrder.update_online_payments_data_with_server(this.pos.orm, 0);
            if (!orderServerOPData) {
                const { confirmed } = await this.popup.add(ConfirmPopup, {
                    title: _t("Online payment unavailable"),
                    body: _t("There is a problem with the server. The order online payment status cannot be retrieved. Are you sure there is no online payment for this order ?"),
                    confirmText: _t("Yes"),
                });
                return confirmed;
            }
            if (orderServerOPData.is_paid) {
                await this.afterPaidOrderSavedOnServer(orderServerOPData.paid_order);
                return false; // Cancel normal flow because the current order is already saved on the server.
            }
            if (orderServerOPData.modified_payment_lines) {
                this.showModifiedOnlinePaymentsPopup();
                return false;
            }
        }

        return true;
    },
    cancelOnlinePayment(order) {
        // Remove the draft order from the server if there is no done online payment
        order.update_online_payments_data_with_server(this.pos.orm, 0);
    },
    showSaveOrderOnServerErrorPopup() {
        this.popup.add(ErrorPopup, {
            title: _t("Online payment unavailable"),
            body: _t("There is a problem with the server. The order cannot be saved and therefore the online payment is not possible."),
        });
    },
    showModifiedOnlinePaymentsPopup() {
        this.popup.add(ErrorPopup, {
            title: _t("Updated online payments"),
            body: _t("There are online payments that were missing in your view."),
        });
    },
    async showOnlinePaymentQrCode(qrCodeData, amount) {
        if (!this.currentOrder.uiState.PaymentScreen) {
            this.currentOrder.uiState.PaymentScreen = {};
        }
        this.currentOrder.uiState.PaymentScreen.onlinePaymentData = {
            amount: amount,
            qrCode: qrCodeData,
            order: this.currentOrder,
        };

        const { confirmed, payload: orderServerOPData } = await this.popup.add(OnlinePaymentPopup, this.currentOrder.uiState.PaymentScreen.onlinePaymentData);

        if (this.currentOrder.uiState.PaymentScreen) {
            delete this.currentOrder.uiState.PaymentScreen.onlinePaymentData;
            if (Object.keys(this.currentOrder.uiState.PaymentScreen).length === 0) {
                delete this.currentOrder.uiState.PaymentScreen;
            }
        }

        return confirmed ? orderServerOPData : null;
    },
    async afterPaidOrderSavedOnServer(orderJSON) {
        if (!orderJSON) {
            this.popup.add(ErrorPopup, {
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
        const orderJSONInArray = [orderJSON];
        await this.pos._loadMissingProducts(orderJSONInArray);
        await this.pos._loadMissingPartners(orderJSONInArray);
        const updatedOrder = this.pos.createReactiveOrder(orderJSON);
        if (!updatedOrder || this.currentOrder.server_id !== updatedOrder.backendId) {
            this.popup.add(ErrorPopup, {
                title: _t("Order saving issue"),
                body: _t("The order has not been saved correctly on the server."),
            });
            return;
        }
        this.pos.orders.add(updatedOrder);
        const oldLocalOrder = this.currentOrder;
        this.pos.set_order(updatedOrder);
        this.pos.removeOrder(oldLocalOrder, false);
        this.pos.validated_orders_name_server_id_map[this.currentOrder.name] = this.currentOrder.id;

        // Now, do practically the normal flow
        if ((this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) && this.pos.config.iface_cashdrawer) {
            this.hardwareProxy.printer.openCashbox();
        }

        this.currentOrder.finalized = true;

        if (isInvoiceRequested) {
            if (!this.currentOrder.account_move) {
                this.popup.add(ErrorPopup, {
                    title: _t("Invoice could not be generated"),
                    body: _t("The invoice could not be generated."),
                });
            } else {
                await this.report.doAction("account.account_invoices", [
                    this.currentOrder.account_move,
                ]);
            }
        }

        await this.postPushOrderResolve([this.currentOrder.server_id]);

        this.afterOrderValidation(true);
    },
});
