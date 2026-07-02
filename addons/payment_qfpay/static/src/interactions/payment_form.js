/* global QFpay */

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { Component, onMounted, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { PaymentForm } from "@payment/interactions/payment_form";

// QFPay requires its wallet element to be rendered outside any <form> element (per QFPay SDK docs).
// To work around this constraint, the wallet UI is rendered inside an Odoo dialog component.
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
        this.qfpayTrackedListeners = [];
        this.qfpayInlineValues = {};
        this.qfpayDialogClose = null;
    },

    /**
     * Override of `payment` to reset the QFPay SDK state when the payment option changes.
     *
     * @override method from @payment/interactions/payment_form
     * @return {void}
     */
    _collapseInlineForms() {
        this._qfpayCleanup();
        return super._collapseInlineForms(...arguments);
    },

    // === DOM MANIPULATION ===

    /**
     * Prepare the inline form of QFPay for direct payment.
     *
     * @override method from @payment/interactions/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "qfpay") {
            await super._prepareInlineForm(...arguments);
            return;
        }

        this._setPaymentFlow("direct");

        try {
            const radio = document.querySelector('input[name="o_payment_radio"]:checked');
            const inlineForm = this._getInlineForm(radio);
            const inlineContext = inlineForm.querySelector(".o_qfpay_inline_context");
            this.qfpayInlineValues = JSON.parse(inlineContext.dataset.qfpayInlineFormValues);
            await this.waitFor(loadJS(this.qfpayInlineValues.sdk_url));
        } catch {
            this._displayErrorDialog(
                _t("Payment Unavailable"),
                _t("Could not load the QFPay payment SDK. Please refresh and try again.")
            );
            this._enableButton();
        }
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Process QFPay implementation of the direct payment flow.
     *
     * @override method from @payment/interactions/payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== "qfpay") {
            await super._processDirectFlow(...arguments);
            return;
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
                                    qfpay
                                        .confirmWalletPayment({ return_url })
                                        .then(resolve)
                                        .catch(reject);
                                } catch (e) {
                                    reject(e);
                                }
                            });
                        },
                    },
                    {
                        onClose: () => {
                            this.qfpayDialogClose = null;
                            this._enableButton();
                        },
                    }
                );
            });
            this._qfpayCleanup();
        } catch (error) {
            this._displayErrorDialog(
                _t("Payment Error"),
                error.message || _t("An unexpected error occurred during payment.")
            );
            this._qfpayCleanup();
            this._enableButton();
        }
    },

    // #=== HELPERS ===#

    /**
     * Wrap a callback to intercept and track any `message` event listeners added by the QFPay SDK.
     *
     * The tracked listeners are stored so they can be removed during cleanup, since the SDK does
     * not expose a teardown API.
     *
     * @private
     * @param {Function} callback - The callback during which listener registration is intercepted.
     * @return {void}
     */
    _qfpayWrapListeners(callback) {
        const origAddEvent = window.addEventListener.bind(window);
        window.addEventListener = (type, listener, options) => {
            if (type === "message") {
                this.qfpayTrackedListeners.push({ listener, options });
            }
            return origAddEvent(type, listener, options);
        };
        try {
            callback();
        } finally {
            window.addEventListener = origAddEvent;
        }
    },

    /**
     * Remove tracked SDK listeners and close the wallet dialog.
     *
     * @private
     * @return {void}
     */
    _qfpayCleanup() {
        for (const { listener, options } of this.qfpayTrackedListeners) {
            window.removeEventListener("message", listener, options);
        }
        this.qfpayTrackedListeners = [];

        if (this.qfpayDialogClose) {
            this.qfpayDialogClose();
            this.qfpayDialogClose = null;
        }
    },
});
