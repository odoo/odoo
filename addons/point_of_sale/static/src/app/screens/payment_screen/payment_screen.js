import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { useErrorHandlers, useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { DatePickerPopup } from "@point_of_sale/app/utils/date_picker_popup/date_picker_popup";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState, onMounted } from "@odoo/owl";
import { Numpad, enhancedButtons } from "@point_of_sale/app/generic_components/numpad/numpad";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { handleRPCError } from "@point_of_sale/app/errors/error_handlers";
import { sprintf } from "@web/core/utils/strings";
import { serializeDateTime } from "@web/core/l10n/dates";

export class PaymentScreen extends Component {
    static template = "point_of_sale.PaymentScreen";
    static components = {
        Numpad,
        PaymentScreenPaymentLines,
        PaymentScreenStatus,
    };
    static props = {
        orderUuid: String,
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.invoiceService = useService("account_move");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.printer = useService("printer");
        this.payment_methods_from_config = this.pos.config.payment_method_ids
            .slice()
            .sort((a, b) => a.sequence - b.sequence);
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use(this._getNumberBufferConfig);
        useErrorHandlers();
        this.payment_interface = null;
        this.error = false;
        this.validateOrder = useAsyncLockedMethod(this.validateOrder);
        onMounted(this.onMounted);
    }

    onMounted() {
        const order = this.pos.get_order();

        for (const payment of order.payment_ids) {
            const pmid = payment.payment_method_id.id;
            if (!this.pos.config.payment_method_ids.map((pm) => pm.id).includes(pmid)) {
                payment.delete({ backend: true });
            }
        }

        if (this.payment_methods_from_config.length == 1 && this.paymentLines.length == 0) {
            this.addNewPaymentLine(this.payment_methods_from_config[0]);
        }
    }

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_color_transparent_6",
            Backspace: "o_colorlist_item_color_transparent_1",
            "+10": "o_colorlist_item_color_transparent_10",
            "+20": "o_colorlist_item_color_transparent_10",
            "+50": "o_colorlist_item_color_transparent_10",
            "-": "o_colorlist_item_color_transparent_3",
        };

        return enhancedButtons().map((button) => ({
            ...button,
            class: `${colorClassMap[button.value] || ""}`,
        }));
    }

    showMaxValueError() {
        this.dialog.add(AlertDialog, {
            title: _t("Maximum value reached"),
            body: _t(
                "The amount cannot be higher than the due amount if you don't have a cash payment method configured."
            ),
        });
    }
    get _getNumberBufferConfig() {
        const config = {
            // When the buffer is updated, trigger this event.
            // Note that the component listens to it.
            triggerAtInput: () => this.updateSelectedPaymentline(),
            useWithBarcode: true,
        };

        return config;
    }
    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    }
    get paymentLines() {
        return this.currentOrder.payment_ids;
    }
    get selectedPaymentLine() {
        return this.currentOrder.get_selected_paymentline();
    }
    async addNewPaymentLine(paymentMethod) {
        if (
            paymentMethod.type === "pay_later" &&
            (!this.currentOrder.to_invoice ||
                this.pos.models["ir.module.module"].find((m) => m.name === "pos_settle_due")
                    ?.state !== "installed")
        ) {
            this.notification.add(
                _t(
                    "To ensure due balance follow-up, generate an invoice or download the accounting application. "
                ),
                { autocloseDelay: 7000, title: _t("Warning") }
            );
        }
        if (this.pos.paymentTerminalInProgress && paymentMethod.use_payment_terminal) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return;
        }

        // original function: click_paymentmethods
        const result = this.currentOrder.add_paymentline(paymentMethod);
        if (!this.check_cash_rounding_has_been_well_applied()) {
            return;
        }
        if (result) {
            this.numberBuffer.reset();
            if (
                paymentMethod.use_payment_terminal &&
                (paymentMethod.payment_terminal?.fast_payments ?? true)
            ) {
                const newPaymentLine = this.paymentLines.at(-1);
                this.sendPaymentRequest(newPaymentLine);
            }
            return true;
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
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
        const payment_terminal = this.selectedPaymentLine.payment_method_id.payment_terminal;
        const hasCashPaymentMethod = this.payment_methods_from_config.some(
            (method) => method.type === "cash"
        );
        if (
            !hasCashPaymentMethod &&
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
            this.deletePaymentLine(this.selectedPaymentLine.uuid);
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

        this.dialog.add(NumberPopup, {
            title: tip ? _t("Change Tip") : _t("Add Tip"),
            startingValue: this.env.utils.formatCurrency(value, false),
            formatDisplayedValue: (x) => `${this.pos.currency.symbol} ${x}`,
            getPayload: async (num) => {
                await this.pos.set_tip(parseFloat(num ?? ""));
            },
        });
    }
    async toggleShippingDatePicker() {
        if (!this.currentOrder.getShippingDate()) {
            this.dialog.add(DatePickerPopup, {
                title: _t("Select the shipping date"),
                getPayload: (shippingDate) => {
                    this.currentOrder.setShippingDate(shippingDate);
                },
            });
        } else {
            this.currentOrder.setShippingDate(false);
        }
    }
    deletePaymentLine(uuid) {
        const line = this.paymentLines.find((line) => line.uuid === uuid);
        if (line.payment_method_id.payment_method_type === "qr_code") {
            this.currentOrder.remove_paymentline(line);
            this.numberBuffer.reset();
            return;
        }
        // If a paymentline with a payment terminal linked to
        // it is removed, the terminal should get a cancel
        // request.
        if (
            ["waiting", "waitingCard", "timeout"].includes(line.get_payment_status()) &&
            line.payment_method_id.payment_terminal
        ) {
            line.set_payment_status("waitingCancel");
            line.payment_method_id.payment_terminal
                .send_payment_cancel(this.currentOrder, uuid)
                .then(() => {
                    this.currentOrder.remove_paymentline(line);
                    this.numberBuffer.reset();
                });
        } else if (line.get_payment_status() !== "waitingCancel") {
            this.currentOrder.remove_paymentline(line);
            this.numberBuffer.reset();
        }
    }
    selectPaymentLine(uuid) {
        const line = this.paymentLines.find((line) => line.uuid === uuid);
        this.currentOrder.select_paymentline(line);
        this.numberBuffer.reset();
    }
    async validateOrder(isForceValidate) {
        this.numberBuffer.capture();
        if (!this.check_cash_rounding_has_been_well_applied()) {
            return;
        }
        const linesToRemove = this.currentOrder.lines.filter((line) => {
            const rounding = line.product_id.uom_id.rounding;
            const decimals = Math.max(0, Math.ceil(-Math.log10(rounding)));
            return floatIsZero(line.qty, decimals);
        });
        for (const line of linesToRemove) {
            this.currentOrder.removeOrderline(line);
        }
        if (await this._isOrderValid(isForceValidate)) {
            // remove pending payments before finalizing the validation
            const toRemove = [];
            for (const line of this.paymentLines) {
                if (!line.is_done() || line.amount === 0) {
                    toRemove.push(line);
                }
            }

            for (const line of toRemove) {
                this.currentOrder.remove_paymentline(line);
            }
            await this._finalizeValidation();
        }
    }
    async _finalizeValidation() {
        if (this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) {
            this.hardwareProxy.openCashbox();
        }

        this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
        for (const line of this.paymentLines) {
            if (!line.amount === 0) {
                this.currentOrder.remove_paymentline(line);
            }
        }

        this.pos.addPendingOrder([this.currentOrder.id]);
        this.currentOrder.state = "paid";

        this.env.services.ui.block();
        let syncOrderResult;
        try {
            // 1. Save order to server.
            syncOrderResult = await this.pos.syncAllOrders({ throw: true });
            if (!syncOrderResult) {
                return;
            }

            // 2. Invoice.
            if (this.shouldDownloadInvoice() && this.currentOrder.is_to_invoice()) {
                if (this.currentOrder.raw.account_move) {
                    await this.invoiceService.downloadPdf(this.currentOrder.raw.account_move);
                } else {
                    throw {
                        code: 401,
                        message: "Backend Invoice",
                        data: { order: this.currentOrder },
                    };
                }
            }
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.pos.showScreen(this.nextScreen);
                Promise.reject(error);
            } else if (error instanceof RPCError) {
                this.currentOrder.state = "draft";
                handleRPCError(error, this.dialog);
            } else {
                throw error;
            }
            return error;
        } finally {
            this.env.services.ui.unblock();
        }

        // 3. Post process.
        const postPushOrders = syncOrderResult.filter((order) => order.wait_for_push_order());
        if (postPushOrders.length > 0) {
            await this.postPushOrderResolve(postPushOrders.map((order) => order.id));
        }

        await this.afterOrderValidation(!!syncOrderResult && syncOrderResult.length > 0);
    }
    async postPushOrderResolve(ordersServerId) {
        const postPushResult = await this._postPushOrderResolve(this.currentOrder, ordersServerId);
        if (!postPushResult) {
            this.dialog.add(AlertDialog, {
                title: _t("Error: no internet connection."),
                body: _t("Some, if not all, post-processing after syncing order failed."),
            });
        }
    }
    async afterOrderValidation() {
        // Always show the next screen regardless of error since pos has to
        // continue working even offline.
        let nextScreen = this.nextScreen;
        let switchScreen = true;

        if (
            nextScreen === "ReceiptScreen" &&
            this.currentOrder.nb_print === 0 &&
            this.pos.config.iface_print_auto
        ) {
            const invoiced_finalized = this.currentOrder.is_to_invoice()
                ? this.currentOrder.finalized
                : true;

            if (invoiced_finalized) {
                this.pos.printReceipt(this.currentOrder);

                if (this.pos.config.iface_print_skip_screen) {
                    this.currentOrder.set_screen_data({ name: "" });
                    this.currentOrder.uiState.locked = true;
                    switchScreen = this.currentOrder.uuid === this.pos.selectedOrderUuid;
                    nextScreen = "ProductScreen";
                    if (switchScreen) {
                        this.selectNextOrder();
                    }
                }
            }
        }

        if (switchScreen) {
            this.pos.showScreen(nextScreen);
        }
    }
    selectNextOrder() {
        if (this.currentOrder.originalSplittedOrder) {
            this.pos.selectedOrderUuid = this.currentOrder.originalSplittedOrder.uuid;
        } else {
            this.pos.add_new_order();
        }
    }
    /**
     * This method is meant to be overriden by localization that do not want to print the invoice pdf
     * every time they create an account move.
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
    async _askForCustomerIfRequired() {
        const splitPayments = this.paymentLines.filter(
            (payment) => payment.payment_method_id.split_transactions
        );
        if (splitPayments.length && !this.currentOrder.get_partner()) {
            const paymentMethod = splitPayments[0].payment_method_id;
            const confirmed = await ask(this.dialog, {
                title: _t("Customer Required"),
                body: _t("Customer is required for %s payment method.", paymentMethod.name),
            });
            if (confirmed) {
                this.pos.selectPartner();
            }
            return false;
        }
    }

    async _isOrderValid(isForceValidate) {
        if (this.currentOrder.get_orderlines().length === 0 && this.currentOrder.is_to_invoice()) {
            this.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t(
                    "There must be at least one product in your order before it can be validated and invoiced."
                ),
            });
            return false;
        }

        if ((await this._askForCustomerIfRequired()) === false) {
            return false;
        }

        if (
            (this.currentOrder.is_to_invoice() || this.currentOrder.getShippingDate()) &&
            !this.currentOrder.get_partner()
        ) {
            const confirmed = await ask(this.dialog, {
                title: _t("Please select the Customer"),
                body: _t(
                    "You need to select the customer before you can invoice or ship an order."
                ),
            });
            if (confirmed) {
                this.pos.selectPartner();
            }
            return false;
        }

        const partner = this.currentOrder.get_partner();
        if (
            this.currentOrder.getShippingDate() &&
            !(partner.name && partner.street && partner.city && partner.country_id)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }

        if (
            !floatIsZero(
                this.currentOrder.get_total_with_tax(),
                this.pos.currency.decimal_places
            ) &&
            this.currentOrder.payment_ids.length === 0
        ) {
            this.notification.add(_t("Select a payment method to validate the order."));
            return false;
        }

        if (!this.currentOrder.is_paid() || this.invoicing) {
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
            if (!this.pos.models["pos.payment.method"].some((pm) => pm.is_cash_count)) {
                this.dialog.add(AlertDialog, {
                    title: _t("Cannot return change without a cash payment method"),
                    body: _t(
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
            this.dialog.add(ConfirmationDialog, {
                title: _t("Please Confirm Large Amount"),
                body:
                    _t("Are you sure that the customer wants to  pay") +
                    " " +
                    this.env.utils.formatCurrency(this.currentOrder.get_total_paid()) +
                    " " +
                    _t("for an order of") +
                    " " +
                    this.env.utils.formatCurrency(this.currentOrder.get_total_with_tax()) +
                    " " +
                    _t('? Clicking "Confirm" will validate the payment.'),
                confirm: () => this.validateOrder(true),
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
        this.pos.paymentTerminalInProgress = true;
        this.numberBuffer.capture();
        this.paymentLines.forEach(function (line) {
            line.can_be_reversed = false;
        });

        let isPaymentSuccessful = false;
        if (line.payment_method_id.payment_method_type === "qr_code") {
            const resp = await this.pos.showQR(line);
            isPaymentSuccessful = line.handle_payment_response(resp);
        } else {
            isPaymentSuccessful = await line.pay();
        }

        // Automatically validate the order when after an electronic payment,
        // the current order is fully paid and due is zero.
        this.pos.paymentTerminalInProgress = false;
        const config = this.pos.config;
        const currency = this.pos.currency;
        const currentOrder = line.pos_order_id;
        if (
            isPaymentSuccessful &&
            currentOrder.is_paid() &&
            floatIsZero(currentOrder.get_due(), currency.decimal_places) &&
            config.auto_validate_terminal_payment
        ) {
            this.validateOrder(false);
        }
    }
    async sendPaymentCancel(line) {
        const payment_terminal = line.payment_method_id.payment_terminal;
        line.set_payment_status("waitingCancel");
        const isCancelSuccessful = await payment_terminal.send_payment_cancel(
            this.currentOrder,
            line.uuid
        );
        if (isCancelSuccessful) {
            line.set_payment_status("retry");
            this.pos.paymentTerminalInProgress = false;
        } else {
            line.set_payment_status("waitingCard");
        }
    }
    async sendPaymentReverse(line) {
        const payment_terminal = line.payment_method_id.payment_terminal;
        line.set_payment_status("reversing");

        const isReversalSuccessful = await payment_terminal.send_payment_reversal(line.uuid);
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

    check_cash_rounding_has_been_well_applied() {
        const cashRounding = this.pos.config.rounding_method;
        if (!cashRounding) {
            return true;
        }

        const order = this.pos.get_order();
        const currency = this.pos.currency;
        for (const payment of order.payment_ids) {
            if (!payment.payment_method_id.is_cash_count) {
                continue;
            }

            const amountPaid = payment.get_amount();
            const expectedAmountPaid = roundPrecision(
                amountPaid,
                cashRounding.rounding,
                cashRounding.rounding_method
            );
            if (floatIsZero(expectedAmountPaid - amountPaid, currency.decimal_places)) {
                continue;
            }

            this.dialog.add(AlertDialog, {
                title: _t("Rounding error in payment lines"),
                body: sprintf(
                    _t(
                        "The amount of your payment lines must be rounded to validate the transaction.\n" +
                            "The rounding precision is %s so you should set %s as payment amount instead of %s."
                    ),
                    cashRounding.rounding.toFixed(this.pos.currency.decimal_places),
                    expectedAmountPaid.toFixed(this.pos.currency.decimal_places),
                    amountPaid.toFixed(this.pos.currency.decimal_places)
                ),
            });
            return false;
        }
        return true;
    }
}

registry.category("pos_screens").add("PaymentScreen", PaymentScreen);
