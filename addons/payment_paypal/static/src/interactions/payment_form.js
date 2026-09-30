/* global paypal */

import { loadJS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    setup() {
        super.setup();
        this.paypalData = {}; // Store the component of each instantiated payment method.
        this.selectedOptionId = undefined;
    },

    // #=== DOM MANIPULATION ===#

    /**
     * @override
     */
    async willStart() {
        // Suffix the button IDs to prevent collisions when multiple button containers are present.
        const paypalEnabledButtons = [...document.querySelectorAll('#o_paypal_enabled_button')];
        const paypalDisabledButtons = [...document.querySelectorAll('#o_paypal_disabled_button')];
        paypalEnabledButtons.forEach((button, index) => button.id += `_${index}`);
        paypalDisabledButtons.forEach((button, index) => button.id += `_${index}`);

        await super.willStart(...arguments);
    },

    /**
     * Hides paypal button container if the expanded inline form is another provider.
     *
     * @private
     * @param {HTMLInputElement} radio - The radio button linked to the payment option.
     * @return {void}
     */
    async _expandInlineForm(radio) {
        const providerCode = this._getProviderCode(radio);
        if (providerCode !== 'paypal') {
            for (const buttonContainer of document.querySelectorAll('#o_paypal_button_container')) {
                buttonContainer.classList.add('d-none');
            }
        }
        await super._expandInlineForm(...arguments);
    },

    /**
     * Prepare the inline form of Paypal for direct payment.
     *
     * The PayPal SDK creates payment buttons based on the client_id and the currency of the order.
     *
     * Two payment buttons are created for each button container: one enabled and one disabled. The
     * enabled button is shown when the user is allowed to click on it, and the disabled button is
     * shown otherwise. This trick is necessary as the PayPal SDK does not provide a way to disable
     * the button after it has been created.
     *
     * The created buttons are saved and reused when switching between different payment methods to
     * avoid recreating the buttons.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'paypal') {
            await super._prepareInlineForm(...arguments);
            return;
        }

        this._hideInputs();
        this._setPaymentFlow('direct');
        const paypalLoadingList = document.querySelectorAll('#o_paypal_loading');
        for (const paypalLoading of paypalLoadingList) {
            paypalLoading.classList.remove('d-none');
        }

        // Check if instantiation of the component is needed.
        if (this.selectedOptionId && this.selectedOptionId !== paymentOptionId) {
            Object.entries(this.paypalData).forEach(([_key, value]) => {
                value.enabledButtons.forEach(btn => btn.hide());
                value.disabledButtons.forEach(btn => btn.hide());
            });
        }
        const currentPayPalData = this.paypalData[paymentOptionId];
        if (currentPayPalData && this.selectedOptionId !== paymentOptionId) {
            const paypalSDKURL = this.paypalData[paymentOptionId]['sdkURL']
            await this.waitFor(this._paypalLoadSDK(paypalSDKURL));
            this.paypalData[this.selectedOptionId]['enabledButtons'].forEach(btn => btn.show());
            this.paypalData[this.selectedOptionId]['disabledButtons'].forEach(btn => btn.show());
        }
        else if (!currentPayPalData) {
            this.paypalData[paymentOptionId] = {};
            const radio = document.querySelector('input[name="o_payment_radio"]:checked');
            let inlineFormValues;
            let paypalColor = 'blue';
            if (radio) {
                inlineFormValues = JSON.parse(radio.dataset['paypalInlineFormValues']);
                paypalColor = radio.dataset['paypalColor'];
            }

            // https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
            const { client_id, currency_code } = inlineFormValues;
            const paypalSDKURL = `https://www.paypal.com/sdk/js?client-id=${
                client_id}&components=buttons&currency=${currency_code}&intent=capture`;
            this.paypalData[paymentOptionId]['sdkURL'] = paypalSDKURL;
            await this.waitFor(this._paypalLoadSDK(paypalSDKURL));

            // Create the two sets of PayPal buttons.
            // See https://developer.paypal.com/sdk/js/reference.
            this.paypalData[paymentOptionId]['enabledButtons'] = [];
            document.querySelectorAll('[id^="o_paypal_enabled_button"]').forEach(domButton => {
                const enabledButton = paypal.Buttons({
                    fundingSource: paypal.FUNDING.PAYPAL,
                    style: { // https://developer.paypal.com/sdk/js/reference/#link-style
                        color: paypalColor,
                        label: 'paypal',
                        disableMaxWidth: true,
                        borderRadius: 6,
                    },
                    createOrder: this._paypalOnClick.bind(this),
                    onApprove: this._paypalOnApprove.bind(this),
                    onCancel: this._paypalOnCancel.bind(this),
                    onError: this._paypalOnError.bind(this),
                });
                enabledButton.render(`#${domButton.id}`);
                this.paypalData[paymentOptionId]['enabledButtons'].push(enabledButton);
            });

            this.paypalData[paymentOptionId]['disabledButtons'] = [];
            document.querySelectorAll('[id^="o_paypal_disabled_button"]').forEach(domButton => {
                const disabledButton = paypal.Buttons({
                    fundingSource: paypal.FUNDING.PAYPAL,
                    style: { // https://developer.paypal.com/sdk/js/reference/#link-style
                        color: 'silver',
                        label: 'paypal',
                        disableMaxWidth: true,
                        borderRadius: 6,
                    },
                    onInit: (data, actions) => actions.disable(),  // Permanently disable the button.
                });
                disabledButton.render(`#${domButton.id}`);
                this.paypalData[paymentOptionId]['disabledButtons'].push(disabledButton);
            });
        }

        for (const paypalLoading of paypalLoadingList) {
            paypalLoading.classList.add('d-none');
        }
        for (const buttonContainer of document.querySelectorAll('#o_paypal_button_container')) {
            buttonContainer.classList.remove('d-none');
        }
        this.selectedOptionId = paymentOptionId;
    },

    /**
     * Load the JS from the PayPal SDK URL and set an identifier dedicated to Odoo, for PayPal to be
     * able to recognize which transactions are originating from Odoo.
     *
     * @private
     * @param {string} paypalSDKURL - The SDK URL that needs to be loaded on the page.
     * @return {void}
     */
    async _paypalLoadSDK(paypalSDKURL) {
        await loadJS(paypalSDKURL);
        const paypalSDKs = document.querySelectorAll(`script[src="${paypalSDKURL}"]`);
        [...paypalSDKs].forEach(sdk => {
            sdk.setAttribute('data-partner-attribution-id', 'OdooInc_SP_EC');
        });
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Handle the click event of the component and initiate the payment.
     *
     * @private
     * @return {void}
     */
    async _paypalOnClick() {
        await this.waitFor(this.submitForm(new Event("PayPalClickEvent")));
        return this.paypalData[this.selectedOptionId].paypalOrderId;
    },

    _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'paypal') {
            super._processDirectFlow(...arguments);
            return;
        }
        this.paypalData[paymentOptionId].paypalOrderId = processingValues['order_id'];
        this.paypalData[paymentOptionId].paypalTxRef = processingValues['reference'];
    },

    /**
     * Handle the approval event of the component and complete the payment.
     *
     * @private
     * @param {object} data - The data returned by PayPal on approving the order.
     * @return {void}
     */
    async _paypalOnApprove(data) {
        const orderID = data.orderID;
        try {
            await this.waitFor(rpc('/payment/paypal/complete_order', {
                'order_id': orderID,
                'reference': this.paypalData[this.selectedOptionId].paypalTxRef,
            }));
            // Close the PayPal buttons that were rendered
            for (const enabledButton of this.paypalData[this.selectedOptionId]['enabledButtons']) {
                enabledButton.close();
            }
            window.location = '/payment/status';
        } catch (error) {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            }
            return Promise.reject(error);
        }
    },

    /**
     * Handle the cancel event of the component.
     * @private
     * @return {void}
     */
    _paypalOnCancel() {
        this._enableButton();
    },

    /**
     * Handle the error event of the component.
     * @private
     * @param {object} error - The error in the component.
     * @return {void}
     */
    _paypalOnError(error) {
        const message = error.message;
        this._enableButton();
        // Paypal throws an error if the popup is closed before it can load;
        // this case should be treated as an onCancel event.
        if (message !== "Detected popup close" && !(error instanceof RPCError)) {
            this._displayErrorDialog(_t("Payment processing failed"), message);
        }
    },
});
