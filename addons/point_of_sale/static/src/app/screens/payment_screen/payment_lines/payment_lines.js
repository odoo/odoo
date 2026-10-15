import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, useProps, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { enhancedButtons } from "@point_of_sale/app/components/numpad/numpad";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

export const paymentScreenPaymentLinesProps = {
    paymentLines: t.array(t.instanceOf(PosPayment)).optional(),
    deleteLine: t.function(),
    selectLine: t.function(),
    sendForceDone: t.function(),
    sendForceCancel: t.function(),
    sendPaymentCancel: t.function(),
    sendPaymentRequest: t.function(),
    updateSelectedPaymentline: t.function(),
};
export class PaymentScreenPaymentLines extends Component {
    static template = "point_of_sale.PaymentScreenPaymentLines";
    static components = { PriceFormatter };
    props = useProps(paymentScreenPaymentLinesProps);

    setup() {
        this.ui = useService("ui");
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    get paymentLines() {
        return this.props.paymentLines.filter((line) => line.payment_method_id);
    }

    getFormattedPrice(line) {
        const amount = line.amount_currency || line.amount;
        return this.pos.formatCurrency(amount, line.currency.id);
    }

    async selectLine(paymentline) {
        this.props.selectLine(paymentline.uuid);
        if (this.ui.isSmall && paymentline.isAmountEditable) {
            this.dialog.add(NumberPopup, {
                title: _t("New amount"),
                buttons: enhancedButtons(),
                startingValue: this.pos.formatCurrency(
                    paymentline.getAmount(),
                    this.pos.config.currency_id.id,
                    { noSymbol: true }
                ),
                getPayload: (num) => {
                    this.props.updateSelectedPaymentline(parseFloat(num));
                },
            });
        }
    }

    showQrCode(line) {
        this.pos.displayQrCode(line);
    }

    /**
     * Get the controls displayed around the payment info of the given line.
     * Controls with an `action` are rendered as buttons, the others as indicators.
     * @returns {{start: Array<PaymentLineControl>, end: Array<PaymentLineControl>}}
     *
     * @typedef {Object} PaymentLineControl
     * @property {string} id                      - Unique identifier for the control.
     * @property {string} icon                    - Icon displayed in the control.
     * @property {string} [iconClass]             - Additional classes for the icon.
     * @property {string} [classes]               - Additional CSS classes to apply to the control.
     * @property {string} [title]                 - Title and aria-label of the control.
     * @property {Function} [action]              - Callback executed when the control is clicked.
     * @property {boolean} [disabled]             - Whether the button is disabled.
     */
    getLineControls(line) {
        const controls = { start: [], end: [] };

        if (line.useQrPayment) {
            controls.start.push({
                id: "qr_code",
                icon: "qr_code",
                classes: "paymentline_show_qr_code ms-2 ps-3",
                title: _t("Show QR Code"),
                action: () => this.showQrCode(line),
                disabled: !line.qr_code || !line.isProcessing,
            });
        }

        if (!line.isSelected() && line.isProcessing) {
            controls.end.push({
                id: "spinner",
                icon: "autorenew",
                iconClass: "oi-spin",
                classes: "payment-spinner mx-2 px-3",
            });
        } else if (line.payment_status !== "done") {
            controls.end.push({
                id: "delete",
                icon: "close_small",
                iconClass: "text-danger",
                classes: "delete-button mx-2 px-3",
                title: _t("Delete"),
                action: () => this.props.deleteLine(line.uuid),
            });
        }

        return controls;
    }

    /**
     * Get the actions that can be offered on the given payment line.
     * @returns {Object<string, PaymentAction>}
     *
     * @typedef {Object} PaymentAction
     * @property {string} id                      - Unique identifier for the action.
     * @property {string} label                   - Text displayed on the action button.
     * @property {string} [title]                 - Title of the button. If not provided, `label` is used.
     * @property {Function} action                - Callback executed when the button is clicked.
     * @property {string} severity                - Bootstrap color variant (e.g., "danger", "warning", "success", "info", ...).
     */
    getPaymentActions(line) {
        return {
            send: {
                id: "send",
                label: _t("Send"),
                title: _t("Send Payment Request"),
                action: () => this.props.sendPaymentRequest(line),
                severity: "primary",
            },
            retry: {
                id: "retry",
                label: _t("Retry"),
                title: _t("Retry Payment Request"),
                action: () => this.props.sendPaymentRequest(line),
                severity: "primary",
            },
            refund: {
                id: "refund",
                label: _t("Refund"),
                title: _t("Send Refund Request"),
                action: () => this.props.sendPaymentRequest(line),
                severity: "primary",
            },
            forceDone: {
                id: "force_done",
                label: _t("Force done"),
                action: () => this.props.sendForceDone(line),
                severity: "warning",
            },
            cancel: {
                id: "cancel",
                label: _t("Cancel"),
                title: _t("Send Cancel Request"),
                action: () => this.props.sendPaymentCancel(line),
                severity: "danger",
            },
            forceCancel: {
                id: "force_cancel",
                label: _t("Force Cancel"),
                action: () => this.props.sendForceCancel(line),
                severity: "danger",
            },
        };
    }

    /**
     * Get the payment action state for the given payment line.
     * @returns {PaymentActionState|null}
     *
     * @typedef {Object} PaymentActionState
     * @property {string} id                      - The payment status of the line.
     * @property {string} title                   - Title of the payment status section.
     * @property {Array<PaymentAction>} actions   - Actions available for the current payment state.
     * @property {string} [icon]                  - Icon shown next to the title, the spinner while processing.
     */
    getPaymentActionState(line) {
        if (line.useBankTransfer && line.payment_status === "waiting") {
            return null;
        }

        const isRefund = line.isRefund;
        const a = this.getPaymentActions(line);
        const waitingCustomerActions = isRefund ? [a.forceDone] : [a.forceDone, a.cancel];
        const states = {
            pending: {
                title: isRefund ? _t("Refund available") : _t("Payment request pending"),
                actions: [isRefund ? a.refund : a.send],
            },
            retry: { title: _t("Transaction failed"), actions: [a.retry] },
            force_done: { title: _t("Connection error"), actions: [a.forceDone] },
            waiting_card: {
                title: isRefund ? _t("Refund in process") : _t("Waiting for card"),
                actions: waitingCustomerActions,
            },
            waiting_scan: {
                title: isRefund
                    ? _t("Refund in process")
                    : _t("Waiting for the customer to scan the QR Code"),
                actions: waitingCustomerActions,
            },
            waiting: { title: _t("Request sent"), actions: [a.forceDone] },
            waiting_cancel: { title: _t("Request sent"), actions: [a.forceCancel] },
            waiting_capture: { title: _t("Request sent"), actions: [] },
            done: {
                title: isRefund ? _t("Refund Successful") : _t("Payment Successful"),
                actions: [],
            },
        };

        const state = states[line.payment_status];
        if (!line.usePaymentInterface || !state) {
            return null;
        }
        state.id = line.payment_status;
        if (line.isProcessing) {
            state.icon = "autorenew";
        }
        return state;
    }
}
