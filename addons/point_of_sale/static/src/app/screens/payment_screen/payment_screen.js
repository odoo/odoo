/** @odoo-module native */
import { Component, onMounted } from "@odoo/owl";
import { enhancedButtons, Numpad } from "@point_of_sale/app/components/numpad/numpad";
import { DatePickerPopup } from "@point_of_sale/app/components/popups/date_picker_popup/date_picker_popup";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { parseFloat } from "@web/core/parsers";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/ui/dialog";
const log = makeLogger("pos.screen.payment");

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
        useLifecycleLog(log);
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.invoiceService = useService("account_move");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.printer = useService("printer");
        this.payment_methods_from_config = this.pos.config.orderedPaymentMethods;
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use(this._getNumberBufferConfig);
        useRouterParamsChecker();
        this.payment_interface = null;
        this.error = false;
        this.validateOrder = useAsyncLockedMethod(this.validateOrder);
        onMounted(this.onMounted);
    }

    async validateOrder(isForceValidate = false) {
        log.logic("validateOrder", () => ({
            order: this.currentOrder.uuid,
            isForceValidate,
            paymentLines: this.paymentLines.length,
        }));
        const validation = new OrderPaymentValidation({
            pos: this.pos,
            orderUuid: this.currentOrder.uuid,
        });
        await validation.validateOrder(isForceValidate);
    }

    onMounted() {
        const order = this.pos.getOrder();

        const configPmIds = new Set(
            this.pos.config.payment_method_ids.map((pm) => pm.id),
        );
        const stale = [...order.payment_ids].filter(
            (payment) => !configPmIds.has(payment.payment_method_id.id),
        );
        for (const payment of stale) {
            payment.delete({ backend: true });
        }

        const autoAddSingleMethod =
            this.payment_methods_from_config.length === 1 &&
            this.paymentLines.length === 0;
        const inheritInvoice =
            this.currentOrder.isRefund &&
            this.currentOrder.lines[0]?.refunded_orderline_id?.order_id?.isToInvoice();
        log.logic("onMounted", () => ({
            order: order.uuid,
            methods: this.payment_methods_from_config.length,
            stalePayments: stale.length,
            autoAddSingleMethod,
            inheritInvoice: Boolean(inheritInvoice),
        }));
        if (autoAddSingleMethod) {
            this.addNewPaymentLine(this.payment_methods_from_config[0]);
        }

        if (inheritInvoice) {
            this.currentOrder.setToInvoice(true);
        }
    }

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]:
                "o_colorlist_item_numpad_color_6",
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
                "The amount cannot be higher than the due amount if you don't have a cash payment method configured.",
            ),
        });
    }
    get _getNumberBufferConfig() {
        const config = {
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
        log.logic("addNewPaymentLine", () => ({
            order: this.currentOrder.uuid,
            method: paymentMethod.id,
            terminal: paymentMethod.use_payment_terminal,
        }));
        if (this.pos.paymentTerminalInProgress && paymentMethod.use_payment_terminal) {
            log.logic("addNewPaymentLine: terminal busy", () => ({
                order: this.currentOrder.uuid,
                method: paymentMethod.id,
            }));
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return;
        }

        if (this.paymentLines.length === 0) {
            this.makeAnimation();
        }
        const result = this.currentOrder.addPaymentline(paymentMethod);
        log.logic("addNewPaymentLine: result", () => ({
            order: this.currentOrder.uuid,
            status: result.status,
            payment: result.status ? result.data.uuid : undefined,
            fastPayment: Boolean(
                result.status &&
                paymentMethod.use_payment_terminal &&
                !this.isRefundOrder &&
                paymentMethod.payment_terminal.fastPayments,
            ),
        }));
        if (result.status) {
            this.numberBuffer.set(result.data.amount.toString());
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
                body: result.data,
            });
            return false;
        }
    }
    updateSelectedPaymentline(amount = false) {
        if (this.paymentLines.length === 0) {
            this.currentOrder.addPaymentline(this.payment_methods_from_config[0]);
        }
        if (!this.selectedPaymentLine) {
            return;
        }
        if (amount === false) {
            if (this.numberBuffer.get() === null) {
                amount = null;
            } else if (this.numberBuffer.get() === "") {
                amount = 0;
            } else {
                amount = this.numberBuffer.getFloat();
            }
        }
        const payment_terminal =
            this.selectedPaymentLine.payment_method_id.payment_terminal;
        const terminalLocked =
            payment_terminal &&
            !["pending", "retry"].includes(this.selectedPaymentLine.getPaymentStatus());
        const hasCashPaymentMethod = this.payment_methods_from_config.some(
            (method) => method.type === "cash",
        );
        const overMax =
            !hasCashPaymentMethod &&
            amount > this.currentOrder.remainingDue + this.selectedPaymentLine.amount;
        log.logic("updateSelectedPaymentline", () => ({
            order: this.currentOrder.uuid,
            payment: this.selectedPaymentLine.uuid,
            amount,
            status: this.selectedPaymentLine.getPaymentStatus(),
            terminalLocked: Boolean(terminalLocked),
            hasCashPaymentMethod,
            overMax,
            remove: amount === null,
        }));
        if (terminalLocked) {
            return;
        }
        if (overMax) {
            this.selectedPaymentLine.setAmount(0);
            this.numberBuffer.set(this.currentOrder.remainingDue.toString());
            amount = this.currentOrder.remainingDue;
            this.showMaxValueError();
        }
        if (amount === null) {
            this.removePaymentLine(this.selectedPaymentLine.uuid);
        } else {
            this.selectedPaymentLine.setAmount(amount);
        }
    }
    async toggleIsToInvoice() {
        log.logic("toggleIsToInvoice", () => ({
            order: this.currentOrder.uuid,
            canInvoice: this.pos.config.canInvoice,
            current: this.currentOrder.isToInvoice(),
        }));
        if (!this.pos.config.canInvoice) {
            this.notification.add(
                _t(
                    "To enable invoice creation, please add a journal for it in the settings.",
                ),
                { type: "warning" },
            );
            return;
        }

        this.currentOrder.setToInvoice(!this.currentOrder.isToInvoice());
    }
    openCashbox() {
        this.hardwareProxy.openCashbox();
    }
    async addTip() {
        this.numberBuffer.capture();
        const tip = this.currentOrder.getTip();
        const change = Math.abs(this.currentOrder.change);
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
        log.logic("addTip", () => ({
            order: this.currentOrder.uuid,
            previous: tip,
            change,
            newTip,
            paymentLine: pLine ? pLine.uuid : false,
        }));

        if (!pLine || this.pos.currency.isZero(parseFloat(newTip) - tip)) {
            if (!pLine) {
                this.notification.add(
                    _t(
                        "The tip has been added to the order. However, the selected payment line does not allow tips to be added.",
                    ),
                );
            }
            return;
        }
        const tipDifference = parseFloat(newTip) - (tip || 0);
        const tipToAdd =
            change <= 0 ? tipDifference : Math.max(0, tipDifference - change);
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
    async removePaymentLine(uuid) {
        const line = this.paymentLines.find((line) => line.uuid === uuid);
        log.logic("removePaymentLine", () => ({
            order: this.currentOrder.uuid,
            payment: uuid,
            type: line.payment_method_id.payment_method_type,
            status: line.getPaymentStatus(),
        }));
        if (line.payment_method_id.payment_method_type === "qr_code") {
            this.currentOrder.removePaymentline(line);
            this.numberBuffer.reset();
            return;
        }
        if (["waiting", "waitingCard", "timeout"].includes(line.getPaymentStatus())) {
            const previousStatus = line.getPaymentStatus();
            line.setPaymentStatus("waitingCancel");
            try {
                await line.payment_method_id.payment_terminal.sendPaymentCancel(
                    this.currentOrder,
                    uuid,
                );
                this.currentOrder.removePaymentline(line);
                this.numberBuffer.reset();
            } catch {
                line.setPaymentStatus(previousStatus);
            }
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
        log.pipeline("sendPaymentRequest", () => ({
            order: this.currentOrder.uuid,
            line: line.uuid,
            amount: line.amount,
            method: line.payment_method_id?.id,
        }));
        this.pos.paymentTerminalInProgress = true;
        this.numberBuffer.capture();
        this.paymentLines.forEach(function (line) {
            line.can_be_reversed = false;
        });

        let isPaymentSuccessful;
        const endRequest = log.perf("sendPaymentRequest");
        try {
            if (line.payment_method_id.payment_method_type === "qr_code") {
                const resp = await this.pos.showQR(line);
                isPaymentSuccessful = line.handlePaymentResponse(resp);
            } else {
                isPaymentSuccessful = await line.pay();
            }
        } finally {
            this.pos.paymentTerminalInProgress = false;
            endRequest({ line: line.uuid, successful: Boolean(isPaymentSuccessful) });
        }

        const config = this.pos.config;
        const currentOrder = line.pos_order_id;
        const autoValidate =
            isPaymentSuccessful &&
            currentOrder.isPaid() &&
            config.auto_validate_terminal_payment &&
            !currentOrder.isRefundInProcess();
        log.logic("sendPaymentRequest: auto validate", () => ({
            order: currentOrder.uuid,
            isPaymentSuccessful: Boolean(isPaymentSuccessful),
            isPaid: currentOrder.isPaid(),
            autoValidateConfig: config.auto_validate_terminal_payment,
            autoValidate: Boolean(autoValidate),
        }));
        if (autoValidate) {
            this.validateOrder(false);
        }
    }
    async sendPaymentCancel(line) {
        const payment_terminal = line.payment_method_id.payment_terminal;
        const previousStatus = line.getPaymentStatus();
        line.setPaymentStatus("waitingCancel");
        log.pipeline("sendPaymentCancel", () => ({
            order: this.currentOrder.uuid,
            line: line.uuid,
            previousStatus,
        }));
        let isCancelSuccessful;
        try {
            isCancelSuccessful = await payment_terminal.sendPaymentCancel(
                this.currentOrder,
                line.uuid,
            );
        } catch {
            log.logic("sendPaymentCancel: threw, restoring", () => ({
                line: line.uuid,
                previousStatus,
            }));
            line.setPaymentStatus(previousStatus);
            return;
        }
        log.logic("sendPaymentCancel: result", () => ({
            line: line.uuid,
            isCancelSuccessful,
        }));
        if (isCancelSuccessful) {
            line.setPaymentStatus("retry");
            this.pos.paymentTerminalInProgress = false;
        } else {
            line.setPaymentStatus("waitingCard");
        }
    }
    async sendPaymentReverse(line) {
        const payment_terminal = line.payment_method_id.payment_terminal;
        const previousStatus = line.getPaymentStatus();
        line.setPaymentStatus("reversing");
        log.pipeline("sendPaymentReverse", () => ({
            order: this.currentOrder.uuid,
            line: line.uuid,
            amount: line.amount,
            previousStatus,
        }));

        let isReversalSuccessful;
        try {
            isReversalSuccessful = await payment_terminal.sendPaymentReversal(
                line.uuid,
            );
        } catch {
            log.logic("sendPaymentReverse: threw, restoring", () => ({
                line: line.uuid,
                previousStatus,
            }));
            line.setPaymentStatus(previousStatus);
            return;
        }
        log.logic("sendPaymentReverse: result", () => ({
            line: line.uuid,
            isReversalSuccessful,
        }));
        if (isReversalSuccessful) {
            line.setAmount(0);
            line.setPaymentStatus("reversed");
        } else {
            line.can_be_reversed = false;
            line.setPaymentStatus("done");
        }
    }
    async sendForceDone(line) {
        log.pipeline("sendForceDone", () => ({
            order: this.currentOrder.uuid,
            line: line.uuid,
            previousStatus: line.getPaymentStatus(),
        }));
        line.setPaymentStatus("done");
        this.pos.paymentTerminalInProgress = false;
        const config = this.pos.config;
        const currentOrder = line.pos_order_id;
        if (
            currentOrder.isPaid() &&
            config.auto_validate_terminal_payment &&
            !currentOrder.isRefundInProcess()
        ) {
            this.validateOrder(false);
        }
    }
    async clickTableGuests() {
        this.pos.setCustomerCount();
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
