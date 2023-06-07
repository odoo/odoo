/** @odoo-module */

import { parseFloat } from "@web/views/fields/parsers";
import { useErrorHandlers } from "@point_of_sale/app/utils/hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { floatIsZero } from "@web/core/utils/numbers";

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { DatePickerPopup } from "@point_of_sale/app/utils/date_picker_popup/date_picker_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

import { PaymentScreenNumpad } from "@point_of_sale/app/screens/payment_screen/numpad/numpad";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";

export class PaymentScreen extends Component {
    static template = "point_of_sale.PaymentScreen";
    static components = {
        PaymentScreenNumpad,
        PaymentScreenPaymentLines,
        PaymentScreenStatus,
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.orm = useService("orm");
        this.popup = useService("popup");
        this.report = useService("report");
        this.notification = useService("pos_notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.payment_methods_from_config = this.pos.payment_methods.filter((method) =>
            this.pos.config.payment_method_ids.includes(method.id)
        );
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use(this._getNumberBufferConfig);
        useErrorHandlers();
        this.payment_interface = null;
        this.error = false;
    }

    showMaxValueError() {
        this.popup.add(ErrorPopup, {
            title: this.env._t("Maximum value reached"),
            body: this.env._t(
                "The amount cannot be higher than the due amount if you don't have a cash payment method configured."
            ),
        });
    }
    get _getNumberBufferConfig() {
        const config = {
            // When the buffer is updated, trigger this event.
            // Note that the component listens to it.
            triggerAtInput: () => this.updateSelectedPaymentline(),
        };

        return config;
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get paymentLines() {
        return this.currentOrder.get_paymentlines();
    }
    get selectedPaymentLine() {
        return this.currentOrder.selected_paymentline;
    }
    async selectPartner() {
        // IMPROVEMENT: This code snippet is repeated multiple times.
        // Maybe it's better to create a function for it.
        const currentPartner = this.currentOrder.get_partner();
        const { confirmed, payload: newPartner } = await this.pos.showTempScreen(
            "PartnerListScreen",
            {
                partner: currentPartner,
            }
        );
        if (confirmed) {
            this.currentOrder.set_partner(newPartner);
            this.currentOrder.updatePricelist(newPartner);
        }
    }
    addNewPaymentLine(paymentMethod) {
        // original function: click_paymentmethods
        const result = this.currentOrder.add_paymentline(paymentMethod);
        if (result) {
            this.numberBuffer.reset();
            return true;
        } else {
            this.popup.add(ErrorPopup, {
                title: this.env._t("Error"),
                body: this.env._t("There is already an electronic payment in progress."),
            });
            return false;
        }
    }
    updateSelectedPaymentline(amount = false) {
        if (this.paymentLines.every((line) => line.paid)) {
            this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
        }
        if (!this.selectedPaymentLine) {
            return;
        } // do nothing if no selected payment line
        if (amount === false) {
            if (this.numberBuffer.get() === null) {
                amount = null;
            } else if (this.numberBuffer.get() === "") {
                amount = 0;
            } else {
                amount = this.numberBuffer.getFloat();
            }
        }
        // disable changing amount on paymentlines with running or done payments on a payment terminal
        const payment_terminal = this.selectedPaymentLine.payment_method.payment_terminal;
        const hasCashPaymentMethod = this.payment_methods_from_config.some(
            (method) => method.type === "cash"
        );
        if (
            !hasCashPaymentMethod &&
            this.currentOrder.get_due() + this.selectedPaymentLine.amount > 0 &&
            amount > this.currentOrder.get_due() + this.selectedPaymentLine.amount
        ) {
            this.selectedPaymentLine.set_amount(0);
            this.numberBuffer.set(this.currentOrder.get_due().toString());
            amount = this.currentOrder.get_due();
            this.showMaxValueError();
        }
        if (
            payment_terminal &&
            !["pending", "retry"].includes(this.selectedPaymentLine.get_payment_status())
        ) {
            return;
        }
        if (amount === null) {
            this.deletePaymentLine(this.selectedPaymentLine.cid);
        } else {
            this.selectedPaymentLine.set_amount(amount);
        }
    }
    toggleIsToInvoice() {
        this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
    }
    openCashbox() {
        this.hardwareProxy.openCashbox();
    }
    async addTip() {
        // click_tip
        const tip = this.currentOrder.get_tip();
        const change = this.currentOrder.get_change();
        const value = tip === 0 && change > 0 ? change : tip;

        const { confirmed, payload } = await this.popup.add(NumberPopup, {
            title: tip ? this.env._t("Change Tip") : this.env._t("Add Tip"),
            startingValue: value,
            isInputSelected: true,
            nbrDecimal: this.pos.currency.decimal_places,
            inputSuffix: this.pos.currency.symbol,
        });

        if (confirmed) {
            this.currentOrder.set_tip(parseFloat(payload));
        }
    }
    async toggleShippingDatePicker() {
        if (!this.currentOrder.getShippingDate()) {
            const { confirmed, payload: shippingDate } = await this.popup.add(DatePickerPopup, {
                title: this.env._t("Select the shipping date"),
            });
            if (confirmed) {
                this.currentOrder.setShippingDate(shippingDate);
            }
        } else {
            this.currentOrder.setShippingDate(false);
        }
    }
    deletePaymentLine(cid) {
        const line = this.paymentLines.find((line) => line.cid === cid);
        // If a paymentline with a payment terminal linked to
        // it is removed, the terminal should get a cancel
        // request.
        if (["waiting", "waitingCard", "timeout"].includes(line.get_payment_status())) {
            line.set_payment_status("waitingCancel");
            line.payment_method.payment_terminal
                .send_payment_cancel(this.currentOrder, cid)
                .then(() => {
                    this.currentOrder.remove_paymentline(line);
                    this.numberBuffer.reset();
                });
        } else if (line.get_payment_status() !== "waitingCancel") {
            this.currentOrder.remove_paymentline(line);
            this.numberBuffer.reset();
        }
    }
    selectPaymentLine(cid) {
        const line = this.paymentLines.find((line) => line.cid === cid);
        this.currentOrder.select_paymentline(line);
        this.numberBuffer.reset();
    }
    async validateOrder(isForceValidate) {
        this.numberBuffer.capture();
        if (this.pos.config.cash_rounding) {
            if (!this.pos.get_order().check_paymentlines_rounding()) {
                this.popup.add(ErrorPopup, {
                    title: this.env._t("Rounding error in payment lines"),
                    body: this.env._t(
                        "The amount of your payment lines must be rounded to validate the transaction."
                    ),
                });
                return;
            }
        }
        if (await this._isOrderValid(isForceValidate)) {
            // remove pending payments before finalizing the validation
            for (const line of this.paymentLines) {
                if (!line.is_done()) {
                    this.currentOrder.remove_paymentline(line);
                }
            }
            await this._finalizeValidation();
        }
    }
    async _finalizeValidation() {
        if (this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) {
            this.hardwareProxy.openCashbox();
        }

        this.currentOrder.initialize_validation_date();
        this.currentOrder.finalized = true;

        let syncOrderResult, hasError;

        try {
            // 1. Save order to server.
            syncOrderResult = await this.pos.push_single_order(this.currentOrder);

            // 2. Invoice.
            if (this.currentOrder.is_to_invoice()) {
                if (syncOrderResult[0]?.account_move) {
                    await this.report.download("account.account_invoices", [
                        syncOrderResult[0].account_move,
                    ]);
                } else {
                    throw {
                        code: 401,
                        message: "Backend Invoice",
                        data: { order: this.currentOrder },
                    };
                }
            }

            // 3. Post process.
            if (syncOrderResult.length && this.currentOrder.wait_for_push_order()) {
                const postPushResult = await this._postPushOrderResolve(
                    this.currentOrder,
                    syncOrderResult.map((res) => res.id)
                );
                if (!postPushResult) {
                    this.popup.add(ErrorPopup, {
                        title: this.env._t("Error: no internet connection."),
                        body: this.env._t(
                            "Some, if not all, post-processing after syncing order failed."
                        ),
                    });
                }
            }
        } catch (error) {
            if (error.code == 700 || error.code == 701) {
                this.error = true;
            }

            if ("code" in error) {
                // We started putting `code` in the rejected object for invoicing error.
                // We can continue with that convention such that when the error has `code`,
                // then it is an error when invoicing. Besides, _handlePushOrderError was
                // introduce to handle invoicing error logic.
                await this._handlePushOrderError(error);
            } else {
                throw error;
            }
        } finally {
            // Always show the next screen regardless of error since pos has to
            // continue working even offline.
            this.pos.showScreen(this.nextScreen);
            // Remove the order from the local storage so that when we refresh the page, the order
            // won't be there
            this.pos.db.remove_unpaid_order(this.currentOrder);

            // Ask the user to sync the remaining unsynced orders.
            if (!hasError && syncOrderResult && this.pos.db.get_orders().length) {
                const { confirmed } = await this.popup.add(ConfirmPopup, {
                    title: this.env._t("Remaining unsynced orders"),
                    body: this.env._t(
                        "There are unsynced orders. Do you want to sync these orders?"
                    ),
                });
                if (confirmed) {
                    // NOTE: Not yet sure if this should be awaited or not.
                    // If awaited, some operations like changing screen
                    // might not work.
                    this.pos.push_orders();
                }
            }
        }
    }
    get nextScreen() {
        return !this.error ? "ReceiptScreen" : "ProductScreen";
    }
    paymentMethodImage(id) {
        if (this.paymentMethod.image) {
            return `/web/image/pos.payment.method/${id}/image`;
        } else if (this.paymentMethod.type === "cash") {
            return "/point_of_sale/static/src/img/money.png";
        } else if (this.paymentMethod.type === "pay_later") {
            return "/point_of_sale/static/src/img/pay-later.png";
        } else {
            return "/point_of_sale/static/src/img/card-bank.png";
        }
    }
    async _isOrderValid(isForceValidate) {
        if (this.currentOrder.get_orderlines().length === 0 && this.currentOrder.is_to_invoice()) {
            this.popup.add(ErrorPopup, {
                title: this.env._t("Empty Order"),
                body: this.env._t(
                    "There must be at least one product in your order before it can be validated and invoiced."
                ),
            });
            return false;
        }

        const splitPayments = this.paymentLines.filter(
            (payment) => payment.payment_method.split_transactions
        );
        if (splitPayments.length && !this.currentOrder.get_partner()) {
            const paymentMethod = splitPayments[0].payment_method;
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Customer Required"),
                body: sprintf(
                    this.env._t("Customer is required for %s payment method."),
                    paymentMethod.name
                ),
            });
            if (confirmed) {
                this.selectPartner();
            }
            return false;
        }

        if (
            (this.currentOrder.is_to_invoice() || this.currentOrder.getShippingDate()) &&
            !this.currentOrder.get_partner()
        ) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Please select the Customer"),
                body: this.env._t(
                    "You need to select the customer before you can invoice or ship an order."
                ),
            });
            if (confirmed) {
                this.selectPartner();
            }
            return false;
        }

        const partner = this.currentOrder.get_partner();
        if (
            this.currentOrder.getShippingDate() &&
            !(partner.name && partner.street && partner.city && partner.country_id)
        ) {
            this.popup.add(ErrorPopup, {
                title: this.env._t("Incorrect address for shipping"),
                body: this.env._t("The selected customer needs an address."),
            });
            return false;
        }

        if (
            this.currentOrder.get_total_with_tax() != 0 &&
            this.currentOrder.get_paymentlines().length === 0
        ) {
            this.notification.add(this.env._t("Select a payment method to validate the order."));
            return false;
        }

        if (!this.currentOrder.is_paid() || this.invoicing) {
            return false;
        }

        if (this.currentOrder.has_not_valid_rounding()) {
            var line = this.currentOrder.has_not_valid_rounding();
            this.popup.add(ErrorPopup, {
                title: this.env._t("Incorrect rounding"),
                body: this.env._t(
                    "You have to round your payments lines." + line.amount + " is not rounded."
                ),
            });
            return false;
        }

        // The exact amount must be paid if there is no cash payment method defined.
        if (
            Math.abs(
                this.currentOrder.get_total_with_tax() -
                    this.currentOrder.get_total_paid() +
                    this.currentOrder.get_rounding_applied()
            ) > 0.00001
        ) {
            if (!this.pos.payment_methods.some((pm) => pm.is_cash_count)) {
                this.popup.add(ErrorPopup, {
                    title: this.env._t("Cannot return change without a cash payment method"),
                    body: this.env._t(
                        "There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration"
                    ),
                });
                return false;
            }
        }

        // if the change is too large, it's probably an input error, make the user confirm.
        if (
            !isForceValidate &&
            this.currentOrder.get_total_with_tax() > 0 &&
            this.currentOrder.get_total_with_tax() * 1000 < this.currentOrder.get_total_paid()
        ) {
            this.popup
                .add(ConfirmPopup, {
                    title: this.env._t("Please Confirm Large Amount"),
                    body:
                        this.env._t("Are you sure that the customer wants to  pay") +
                        " " +
                        this.env.utils.formatCurrency(this.currentOrder.get_total_paid()) +
                        " " +
                        this.env._t("for an order of") +
                        " " +
                        this.env.utils.formatCurrency(this.currentOrder.get_total_with_tax()) +
                        " " +
                        this.env._t('? Clicking "Confirm" will validate the payment.'),
                })
                .then(({ confirmed }) => {
                    if (confirmed) {
                        this.validateOrder(true);
                    }
                });
            return false;
        }

        if (!this.currentOrder._isValidEmptyOrder()) {
            return false;
        }

        return true;
    }
    async _postPushOrderResolve(order, order_server_ids) {
        return true;
    }
    async sendPaymentRequest(line) {
        // Other payment lines can not be reversed anymore
        this.numberBuffer.capture();
        this.paymentLines.forEach(function (line) {
            line.can_be_reversed = false;
        });

        const payment_terminal = line.payment_method.payment_terminal;
        line.set_payment_status("waiting");

        const isPaymentSuccessful = await payment_terminal.send_payment_request(line.cid);
        if (isPaymentSuccessful) {
            line.set_payment_status("done");
            line.can_be_reversed = payment_terminal.supports_reversals;
            // Automatically validate the order when after an electronic payment,
            // the current order is fully paid and due is zero.
            const { config, currency } = this.pos;
            if (
                this.currentOrder.is_paid() &&
                floatIsZero(this.currentOrder.get_due(), currency.decimal_places) &&
                config.auto_validate_terminal_payment
            ) {
                this.validateOrder(false);
            }
        } else {
            line.set_payment_status("retry");
        }
    }
    async sendPaymentCancel(line) {
        const payment_terminal = line.payment_method.payment_terminal;
        line.set_payment_status("waitingCancel");
        const isCancelSuccessful = await payment_terminal.send_payment_cancel(
            this.currentOrder,
            line.cid
        );
        if (isCancelSuccessful) {
            line.set_payment_status("retry");
        } else {
            line.set_payment_status("waitingCard");
        }
    }
    async sendPaymentReverse(line) {
        const payment_terminal = line.payment_method.payment_terminal;
        line.set_payment_status("reversing");

        const isReversalSuccessful = await payment_terminal.send_payment_reversal(line.cid);
        if (isReversalSuccessful) {
            line.set_amount(0);
            line.set_payment_status("reversed");
        } else {
            line.can_be_reversed = false;
            line.set_payment_status("done");
        }
    }
    async sendForceDone(line) {
        line.set_payment_status("done");
    }
}

registry.category("pos_screens").add("PaymentScreen", PaymentScreen);
