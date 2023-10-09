/** @odoo-module */

import { parseFloat } from "@web/views/fields/parsers";
import { useErrorHandlers, useAsyncLockedMethod } from "@point_of_sale/js/custom_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { floatIsZero } from "@web/core/utils/numbers";

import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { DatePickerPopup } from "@point_of_sale/js/Popups/DatePickerPopup";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";

import { PaymentScreenNumpad } from "./PaymentScreenNumpad";
import { PaymentScreenPaymentLines } from "./PaymentScreenPaymentLines";
import { PaymentScreenStatus } from "./PaymentScreenStatus";
import { usePos } from "@point_of_sale/app/pos_hook";
import { Component, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";

export class PaymentScreen extends Component {
    static template = "PaymentScreen";
    static components = {
        PaymentScreenNumpad,
        PaymentScreenPaymentLines,
        PaymentScreenStatus,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.orm = useService("orm");
        this.popup = useService("popup");
        this.report = useService("report");
        this.notification = useService("pos_notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.payment_methods_from_config = this.pos.globalState.payment_methods.filter((method) =>
            this.pos.globalState.config.payment_method_ids.includes(method.id)
        );
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use(this._getNumberBufferConfig);
        useErrorHandlers();
        this.payment_interface = null;
        this.error = false;
        this.validateOrder = useAsyncLockedMethod(this.validateOrder);
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
        // Check if pos has a cash payment method
        const hasCashPaymentMethod = this.payment_methods_from_config.some(
            (method) => method.type === "cash"
        );

        if (!hasCashPaymentMethod) {
            config["maxValue"] = this.currentOrder.get_due();
            config["maxValueReached"] = this.showMaxValueError.bind(this);
        }

        return config;
    }
    get currentOrder() {
        return this.pos.globalState.get_order();
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
    updateSelectedPaymentline() {
        if (this.paymentLines.every((line) => line.paid)) {
            this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
        }
        if (!this.selectedPaymentLine) {
            return;
        } // do nothing if no selected payment line
        // disable changing amount on paymentlines with running or done payments on a payment terminal
        const payment_terminal = this.selectedPaymentLine.payment_method.payment_terminal;
        if (
            payment_terminal &&
            !["pending", "retry"].includes(this.selectedPaymentLine.get_payment_status())
        ) {
            return;
        }
        if (this.numberBuffer.get() === null) {
            this.deletePaymentLine(this.selectedPaymentLine.cid);
        } else {
            this.selectedPaymentLine.set_amount(this.numberBuffer.getFloat());
        }
    }
    toggleIsToInvoice() {
        this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
    }
    openCashbox() {
        this.hardwareProxy.printer.openCashbox();
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
            inputSuffix: this.pos.globalState.currency.symbol,
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
        if (this.pos.globalState.config.cash_rounding) {
            if (!this.pos.globalState.get_order().check_paymentlines_rounding()) {
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
        const { globalState } = this.pos;
        if (
            (this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) &&
            globalState.config.iface_cashdrawer &&
            this.hardwareProxy &&
            this.hardwareProxy.printer
        ) {
            this.hardwareProxy.printer.openCashbox();
        }

        this.currentOrder.initialize_validation_date();
        for (let line of this.paymentLines) {
            if (!line.amount === 0) {
                 this.currentOrder.remove_paymentline(line);
            }
        }
        this.currentOrder.finalized = true;

        let syncOrderResult, hasError;

        try {
            // 1. Save order to server.
            syncOrderResult = await globalState.push_single_order(this.currentOrder);

            // 2. Invoice.
            if (this.shouldDownloadInvoice() && this.currentOrder.is_to_invoice()) {
                if (syncOrderResult.length) {
                    await this.report.doAction("account.account_invoices", [
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
            globalState.db.remove_unpaid_order(this.currentOrder);

            // Ask the user to sync the remaining unsynced orders.
            if (!hasError && syncOrderResult && globalState.db.get_orders().length) {
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
                    globalState.push_orders();
                }
            }
        }
    }
    /**
     * This method is meant to be overriden by localization that do not want to print the invoice pdf
     * every time they create an account move. For example, it can be overriden like this:
     * ```
     * shouldDownloadInvoice() {
     *     const currentCountry = ...
     *     if (currentCountry.code === 'FR') {
     *         return false;
     *     } else {
     *         return super.shouldDownloadInvoice(); // or this._super(...arguments) depending on the odoo version.
     *     }
     * }
     * ```
     * @returns {boolean} true if the invoice pdf should be downloaded
     */
    shouldDownloadInvoice() {
        return true;
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
            if (!this.pos.globalState.payment_methods.some((pm) => pm.is_cash_count)) {
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
            const { config, currency } = this.pos.globalState;
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
