/** @odoo-module */
/* global Xendit */

import { _t } from '@web/core/l10n/translation';
import { loadJS } from '@web/core/assets'

import paymentForm from '@payment/js/payment_form';
import { RPCError } from '@web/core/network/rpc_service';

paymentForm.include({
    xenditData: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Xendit for direct payment.
     *
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
     async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'xendit' || paymentMethodCode != 'card') {
            this._super(...arguments);
            return;
        }

        // Check if the inline form values were already extracted.
        this.xenditData ??= {}; // Store the form data of each instantiated payment method.
        if (flow === 'token') {
            return; // Don't show the form for tokens.
        } else if (this.xenditData[paymentOptionId]) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation.
            loadJS(this.xenditData[paymentOptionId]['xenditURL']); // Reload the SDK.
            return; // Don't re-extract the data if already done for this payment method.
        }

        // Overwrite the flow of the selected payment method.
        this._setPaymentFlow('direct');

        // Extract and deserialize the inline form values.
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(radio);
        const xenditForm = inlineForm.querySelector('[name="o_xendit_form"]');
        this.xenditData[paymentOptionId] = JSON.parse(
            xenditForm.dataset['xenditInlineFormValues']
        );
        let xenditURL = 'https://js.xendit.co/v1/xendit.min.js';
        this.xenditData[paymentOptionId].form = xenditForm;
        this.xenditData[paymentOptionId].xenditURL = xenditURL;

        // Load the SDK.
        loadJS(xenditURL);
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Trigger the payment processing by submitting the data.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
     async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'xendit' || flow === 'token' || paymentMethodCode != 'card') {
            this._super(...arguments); // Tokens are handled by the generic flow
            return;
        }
        const inputs = Object.values(
            this._xenditGetInlineFormInputs(paymentOptionId, paymentMethodCode)
        );
        // Checking the elements
        if (!inputs.every(element => element.reportValidity())) {
            this._enableButton(); // The submit button is disabled at this point, enable it
            return;
        }

        await this._super(...arguments);
    },

    // #=== GETTERS ===#

    /**
     * Return all relevant inline form inputs based on the payment method type of the provider.
     *
     * @private
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @return {Object} - An object mapping the name of inline form inputs to their DOM element
     */
     _xenditGetInlineFormInputs(paymentOptionId, paymentMethodCode) {
        const form = this.xenditData[paymentOptionId]['form'];
        if (paymentMethodCode === 'card') {
            return {
                card: form.querySelector('#o_xendit_card'),
                month: form.querySelector('#o_xendit_month'),
                year: form.querySelector('#o_xendit_year'),
                cvn: form.querySelector('#o_xendit_cvn'),
            };
        }
        return {}
    },

    /**
     * Process the direct payment flow.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
     async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'xendit') {
            this._super(...arguments);
            return;
        }
        // if tokenize, create multi-use token
        const payload = {
            ...this.xenditGetPaymentDetails(paymentOptionId, paymentMethodCode),
            is_multiple_use: true,
            should_authenticate: false,        }

        Xendit.setPublishableKey(this.xenditData[paymentOptionId]['public_key'])
        Xendit.card.createToken(payload, (err, token) => this._xenditHandleResponse(err, token, processingValues))
    },

    /**
     * Handle response after Xendit requests and initiate payment
     *
     * @param {object} err - Error obejct with cause
     * @param {object} token - Token data created
     * @return {void}
     */
    _xenditHandleResponse(err, token, processingValues) {
        console.log(err);
        // error handling
        if (err) {
            this._displayErrorDialog(_t("Payment processing failed"), err.message);
            this._enableButton();
            return;
        }
        if (token.status === "VERIFIED") {
            this.rpc('/payment/xendit/payment', {
                'reference': processingValues.reference,
                'partner_id': processingValues.partner_id,
                'token_data': token,
            }).then(() => {
                window.location = '/payment/status'
            }).catch((error) => {
                if (error instanceof RPCError) {
                    this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                    this._enableButton();
                } else {
                    return Promise.reject(error);
                }
            })
        } else if (token.status === 'IN_REVIEW') {
            window.open(token.payer_authentication_url, 'verification-window', 'popup')
        } else if (token.status === 'FAILED') {
            this._displayErrorDialog(_t("Payment processing failed"), token.failure_reason);
            this._enableButton();
            return;
        }
    },

    /**
     * Return the credit card data to prepare payload for create token request

     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode  - The code of the selected payment method, if any.
     * @return {Object} - Data to pass to the Xendit createToken request
     */
    xenditGetPaymentDetails(paymentOptionId, paymentMethodCode) {
        const inputs = this._xenditGetInlineFormInputs(paymentOptionId, paymentMethodCode);
        if (paymentMethodCode === 'card') {
            return {
                card_number: inputs.card.value.replace(/ /g, ''),
                card_exp_month: inputs.month.value,
                card_exp_year: '20' + inputs.year.value,
                card_cvn: inputs.cvn.value,
            };
        }
    },

})
