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

        if (line.useQr) {
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
     * Get the payment action state for the given payment line.
     * @returns {PaymentActionState}
     *
     * @typedef {Object} PaymentAction
     * @property {string} id                      - Unique identifier for the action.
     * @property {string} label                   - Text displayed on the action button.
     * @property {string} [title]                 - Title of the button. If not provided, `label` is used.
     * @property {Function} action                - Callback executed when the button is clicked.
     * @property {string} classes                 - Additional CSS classes to apply to the button.
     * @property {string} severity                - Bootstrap color variant (e.g., "danger", "warning", "success", "info", ...).
     * @property {boolean} [show]                 - Condition to determine if the action should be displayed (show by default).
     *
     * @typedef {Object} PaymentActionState
     * @property {string} id                      - Unique identifier for the payment state.
     * @property {string} title                   - Title of the payment status section.
     * @property {Array<PaymentAction>} actions   - Actions available for the current payment state.
     * @property {string} [icon]                  - Optional icon representing the payment state.
     * @property {string} [iconClass]            - Additional classes for the icon.
     *
     * @type {PaymentActionState}
     */
    getPaymentActionState(line) {
        const status = line.payment_status;
        const isRefund = line.isRefund;
        const SPINNER_ICON = "autorenew";
        const SPINNER_ICON_CLASS = "oi-spin";
        const ACTIONS = {
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
                show: !isRefund,
            },

            forceCancel: {
                id: "force_cancel",
                label: _t("Force Cancel"),
                action: () => this.props.sendForceCancel(line),
                severity: "danger",
            },
        };
        const state = { title: "", actions: [] };

        // --- Pending
        if (status === "pending") {
            state.id = isRefund ? "refund_available" : "pending";
            state.title = isRefund ? _t("Refund available") : _t("Payment request pending");
            state.actions = [isRefund ? ACTIONS.refund : ACTIONS.send];
        }

        // --- Retry
        else if (status === "retry") {
            state.id = "retry";
            state.title = _t("Transaction failed");
            state.actions = [ACTIONS.retry];
        }

        // --- Force done
        else if (status === "force_done") {
            state.id = "force_done";
            state.title = _t("Connection error");
            state.actions = [ACTIONS.forceDone];
        }

        // --- Waiting customer action
        else if (["waiting_card", "waiting_scan"].includes(status)) {
            const titles = {
                waiting_card: _t("Waiting for card"),
                waiting_scan: _t("Waiting for the customer to scan the QR Code"),
            };

            state.id = isRefund ? "waiting_refund" : status;
            state.title = isRefund ? _t("Refund in process") : titles[status];
            state.icon = SPINNER_ICON;
            state.iconClass = SPINNER_ICON_CLASS;
            state.actions = [ACTIONS.forceDone, ACTIONS.cancel];
        }

        // --- Request sent
        else if (["waiting", "waiting_cancel", "waiting_capture"].includes(status)) {
            state.id = status;
            state.title = _t("Request sent");
            state.icon = SPINNER_ICON;
            state.iconClass = SPINNER_ICON_CLASS;
            state.actions = [
                { ...ACTIONS.forceDone, show: status === "waiting" },
                { ...ACTIONS.forceCancel, show: status === "waiting_cancel" },
            ];
        }

        // --- Done
        else if (status === "done") {
            state.id = isRefund ? "refunded" : "paid";
            state.title = isRefund ? _t("Refund Successful") : _t("Payment Successful");
        }

        // --- Non-electronic payment: no status to show
        else {
            return null;
        }

        return state;
    }
}
