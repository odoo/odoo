import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { useErrorHandlers, useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { DatePickerPopup } from "@point_of_sale/app/components/popups/date_picker_popup/date_picker_popup";

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, onMounted } from "@odoo/owl";
import { Numpad, enhancedButtons } from "@point_of_sale/app/components/numpad/numpad";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

export class PaymentScreen extends Component {
    static template = "point_of_sale.PaymentScreen";
    static components = {
        Numpad,
        PaymentScreenPaymentLines,
        PaymentScreenStatus,
        PriceFormatter,
    };
    static props = {
        orderUuid: String,
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
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
        useRouterParamsChecker();
        useErrorHandlers();
        this.payment_interface = null;
        this.error = false;
        this.validateOrder = useAsyncLockedMethod(this.validateOrder);
        onMounted(this.onMounted);
    }

    async validateOrder(isForceValidate = false) {
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            order: this.currentOrder,
        });
        await validation.validateOrder(isForceValidate);
    }

    onMounted() {
        const order = this.pos.getOrder();

        for (const payment of order.payment_ids) {
            const pmid = payment.payment_method_id.id;
            if (!this.pos.config.payment_method_ids.map((pm) => pm.id).includes(pmid)) {
                payment.delete({ backend: true });
            }
        }

        if (this.payment_methods_from_config.length == 1 && this.paymentLines.length == 0) {
            this.addNewPaymentLine(this.payment_methods_from_config[0]);
        }

        //Activate the invoice option for refund orders if the original order was invoiced.
        if (
            this.currentOrder.isRefund &&
            this.currentOrder.lines[0].refunded_orderline_id?.order_id?.isToInvoice()
        ) {
            this.currentOrder.setToInvoice(true);
        }
    }

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_numpad_color_6",
            Backspace: "o_colorlist_item_numpad_color_1",
            "+10": "o_colorlist_item_numpad_color_10",
            "+20": "o_colorlist_item_numpad_color_10",
            "+50": "o_colorlist_item_numpad_color_10",
            "-": "o_colorlist_item_numpad_color_3",
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
    get isRefundOrder() {
        return this.currentOrder.isRefund;
    }
    get paymentLines() {
        return this.currentOrder.payment_ids;
    }
    get selectedPaymentLine() {
        return this.currentOrder.getSelectedPaymentline();
    }
    makeAnimation() {
        this.pos.addAnimation = true;
        setTimeout(() => (this.pos.addAnimation = false), 1000);
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

        if (this.paymentLines.length === 0) {
            this.makeAnimation();
        }
        // original function: click_paymentmethods
        const result = this.currentOrder.addPaymentline(paymentMethod);
        if (result) {
            this.numberBuffer.set(result.amount.toString());
            if (
                paymentMethod.use_payment_terminal &&
                !this.isRefundOrder &&
                paymentMethod.payment_terminal.fastPayments
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
            this.currentOrder.addPaymentline(this.payment_methods_from_config[0]);
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
            amount > this.currentOrder.getDue() + this.selectedPaymentLine.amount
        ) {
            this.selectedPaymentLine.setAmount(0);
            this.numberBuffer.set(this.currentOrder.getDue().toString());
            amount = this.currentOrder.getDue();
            this.showMaxValueError();
        }
        if (
            payment_terminal &&
            !["pending", "retry"].includes(this.selectedPaymentLine.getPaymentStatus())
        ) {
            return;
        }
        if (amount === null) {
            this.deletePaymentLine(this.selectedPaymentLine.uuid);
        } else {
            this.selectedPaymentLine.setAmount(amount);
        }
    }
    async toggleIsToInvoice() {
        this.currentOrder.setToInvoice(!this.currentOrder.isToInvoice());
    }
    openCashbox() {
        this.hardwareProxy.openCashbox();
    }
    async addTip() {
        const tip = this.currentOrder.getTip();
        const change = this.currentOrder.getChange();
        const value = tip === 0 && change > 0 ? change : tip;
        const newTip = await makeAwaitable(this.dialog, NumberPopup, {
            title: tip ? _t("Change Tip") : _t("Add Tip"),
            startingValue: this.env.utils.formatCurrency(value, false),
            formatDisplayedValue: (x) => `${this.pos.currency.symbol} ${x}`,
        });

        if (newTip === undefined) {
            return;
        }
        await this.pos.setTip(parseFloat(newTip ?? ""));
        const pLine =
            this.selectedPaymentLine &&
            (!this.selectedPaymentLine.isElectronic() ||
                this.selectedPaymentLine.getPaymentStatus() === "pending")
                ? this.selectedPaymentLine
                : false;

        if (!pLine || newTip === tip) {
            this.notification.add(
                _t(
                    "The tip has been added to the order. However,the selected payment line does not allow tips to be added."
                )
            );
            return;
        }
        const tipDifference = parseFloat(newTip) - (tip || 0);
        const tipToAdd = change <= 0 ? tipDifference : Math.max(0, tipDifference - change);
        pLine.setAmount(pLine.getAmount() + tipToAdd);
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
            this.currentOrder.removePaymentline(line);
            this.numberBuffer.reset();
            return;
        }
        // If a paymentline with a payment terminal linked to
        // it is removed, the terminal should get a cancel
        // request.
        if (["waiting", "waitingCard", "timeout"].includes(line.getPaymentStatus())) {
            line.setPaymentStatus("waitingCancel");
            line.payment_method_id.payment_terminal
                .sendPaymentCancel(this.currentOrder, uuid)
                .then(() => {
                    this.currentOrder.removePaymentline(line);
                    this.numberBuffer.reset();
                });
        } else if (line.getPaymentStatus() !== "waitingCancel") {
            this.currentOrder.removePaymentline(line);
            this.numberBuffer.reset();
        }
    }
    selectPaymentLine(uuid) {
        const line = this.paymentLines.find((line) => line.uuid === uuid);
        this.currentOrder.selectPaymentline(line);
        this.numberBuffer.reset();
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
            isPaymentSuccessful = line.handlePaymentResponse(resp);
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
            currentOrder.isPaid() &&
            currency.isZero(currentOrder.getDue()) &&
            config.auto_validate_terminal_payment &&
            !currentOrder.isRefundInProcess()
        ) {
            this.validateOrder(false);
        }
    }
    async sendPaymentCancel(line) {
        const payment_terminal = line.payment_method_id.payment_terminal;
        line.setPaymentStatus("waitingCancel");
        const isCancelSuccessful = await payment_terminal.sendPaymentCancel(
            this.currentOrder,
            line.uuid
        );
        if (isCancelSuccessful) {
            line.setPaymentStatus("retry");
            this.pos.paymentTerminalInProgress = false;
        } else {
            line.setPaymentStatus("waitingCard");
        }
    }
    async sendPaymentReverse(line) {
        const payment_terminal = line.payment_method_id.payment_terminal;
        line.setPaymentStatus("reversing");

        const isReversalSuccessful = await payment_terminal.sendPaymentReversal(line.uuid);
        if (isReversalSuccessful) {
            line.setAmount(0);
            line.setPaymentStatus("reversed");
        } else {
            line.can_be_reversed = false;
            line.setPaymentStatus("done");
        }
    }
    async sendForceDone(line) {
        line.setPaymentStatus("done");
    }
}

registry.category("pos_pages").add("PaymentScreen", {
    name: "PaymentScreen",
    component: PaymentScreen,
    route: `/pos/ui/${odoo.pos_config_id}/payment/{string:orderUuid}`,
    params: {
        orderUuid: true,
        orderFinalized: false,
    },
});
