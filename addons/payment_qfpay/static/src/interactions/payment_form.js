/* global QFpay */

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { Component, onMounted, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { PaymentForm } from "@payment/interactions/payment_form";

const QFPAY_DIALOG_CLOSED = Symbol("qfpay.dialog.closed");

// QFPay requires the wallet element outside any <form>. The wallet UI is rendered inside a dialog.
class QFPayWalletDialog extends Component {
    static components = { Dialog };
    static template = xml`
        <Dialog title="this.props.title" size="'md'">
            <div id="o_qfpay_wallet_dialog_container"/>
        </Dialog>
    `;
    static props = { close: Function, title: String, onMounted: Function };

    setup() {
        onMounted(() => this.props.onMounted());
    }
}

patch(PaymentForm.prototype, {
    setup() {
        super.setup();
        this.qfpayInlineValues = {};
        this.qfpayDialogClose = null;
        this._qfpayAbortController = null;
    },

    /**
     * @override
     */
    _collapseInlineForms() {
        this._qfpayCleanup();
        return super._collapseInlineForms(...arguments);
    },

    // === DOM MANIPULATION ===

    /**
     * @override
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "qfpay") {
            return super._prepareInlineForm(...arguments);
        }
        this._setPaymentFlow("direct");
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(radio);
        const inlineContext = inlineForm?.querySelector(".o_qfpay_inline_context");
        this.qfpayInlineValues = JSON.parse(inlineContext.dataset.qfpayInlineFormValues);
        await this.waitFor(loadJS(this.qfpayInlineValues.sdk_url));
    },

    // === PAYMENT FLOW ===

    /**
     * @override
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== "qfpay") {
            return super._processDirectFlow(...arguments);
        }

        const { payment_intent, out_trade_no, txamt, txcurrcd, return_url } = processingValues;
        const { sdk_env: env, sdk_region: region, picker_payment_type } = this.qfpayInlineValues;

        try {
            const qfpay = QFpay.config({ region, env, sessionId: payment_intent });
            const payment = qfpay.payment();

            await new Promise((resolve, reject) => {
                this.qfpayDialogClose = this.services.dialog.add(
                    QFPayWalletDialog,
                    {
                        title: _t("Complete Your Payment"),
                        onMounted: () => {
                            this._qfpayWrapListeners(() => {
                                try {
                                    qfpay.element({ theme: "default" }).createWallet({
                                        selector: "#o_qfpay_wallet_dialog_container",
                                    });
                                    payment.walletPay(
                                        {
                                            paysource: "payment_element_checkout",
                                            out_trade_no,
                                            txamt,
                                            txcurrcd,
                                            support_pay_type: [picker_payment_type],
                                        },
                                        payment_intent
                                    );
                                    qfpay.confirmWalletPayment({ return_url }).then(resolve, reject);
                                } catch (e) {
                                    reject(e);
                                }
                            });
                        },
                    },
                    {
                        onClose: () => {
                            this.qfpayDialogClose = null;
                            this._qfpayCleanup();
                            this._enableButton();
                            reject(QFPAY_DIALOG_CLOSED);
                        },
                    }
                );
            });
            this._qfpayCleanup();
        } catch (error) {
            if (error !== QFPAY_DIALOG_CLOSED) {
                this._displayErrorDialog(
                    _t("Payment Error"),
                    error.message || _t("An unexpected error occurred during payment.")
                );
            }
            this._qfpayCleanup();
            this._enableButton();
        }
    },

    // === HELPERS ===

    /**
     * Intercept `message` listeners the QFPay SDK registers during `callback` and inject an
     * `AbortSignal` for atomic cleanup via `AbortController.abort()`.
     *
     * @private
     * @param {Function} callback
     */
    _qfpayWrapListeners(callback) {
        const abortController = new AbortController();
        const origAddEvent = window.addEventListener.bind(window);
        window.addEventListener = (type, listener, options) => {
            if (type === "message") {
                const signalOption = typeof options === "object" && options !== null
                    ? { ...options, signal: abortController.signal }
                    : { signal: abortController.signal, capture: !!options };
                return origAddEvent(type, listener, signalOption);
            }
            return origAddEvent(type, listener, options);
        };
        try {
            callback();
            this._qfpayAbortController = abortController;
        } finally {
            window.addEventListener = origAddEvent;
        }
    },

    /**
     * Abort tracked listeners and close the wallet dialog.
     *
     * @private
     */
    _qfpayCleanup() {
        if (this._qfpayAbortController) {
            this._qfpayAbortController.abort();
            this._qfpayAbortController = null;
        }
        if (this.qfpayDialogClose) {
            this.qfpayDialogClose();
            this.qfpayDialogClose = null;
        }
    },
});
