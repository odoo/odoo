/** @odoo-module **/
/* global AdyenCheckout */

import core from "web.core";
import paymentForm from "@payment/js/payment_form";

const _t = core._t;

const adyenMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prepare the inline form of Adyen for direct payment.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentProviderId; - The id of the provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {void}
     */
    async _prepareInlineForm (
        providerCode, paymentProviderId, paymentOptionId, paymentMethodCode, flow
    ) {
        if (providerCode !== 'adyen') {
            this._super(...arguments);
            return;
        }

        // Check if instantiation of the drop-in is needed
        if (flow === 'token') {
            return; // No drop-in for tokens
        } else if (this.adyenDropin && this.adyenDropin.paymentOptionId === paymentOptionId) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
            return; // Don't re-instantiate if already done for this provider
        }

        // Overwrite the flow of the select payment option
        this._setPaymentFlow('direct');

        // Get public information on the provider (state, client_key)
        this._rpc({
            route: '/payment/adyen/provider_info',
            params: {
                'provider_id': paymentProviderId,
            },
        }).then(providerInfo => {
            // Get the available payment methods
            return this._rpc({
                route: '/payment/adyen/payment_methods',
                params: {
                    'provider_id': paymentProviderId,
                    'partner_id': parseInt(this.txContext.partnerId),
                    'amount': this.txContext.amount
                        ? parseFloat(this.txContext.amount)
                        : undefined,
                    'currency_id': this.txContext.currencyId
                        ? parseInt(this.txContext.currencyId)
                        : undefined,
                    'payment_method_code': paymentMethodCode,
                },
            }).then(async response => {
                // Instantiate the drop-in
                const configuration = {
                    paymentMethodsResponse: response.paymentMethodsResult,
                    clientKey: providerInfo.client_key,
                    locale: (this._getContext().lang || 'en-US').replace('_', '-'),
                    environment: providerInfo.state === 'enabled' ? 'live' : 'test',
                    onAdditionalDetails: this._dropinOnAdditionalDetails.bind(this),
                    onError: this._dropinOnError.bind(this),
                    onSubmit: this._dropinOnSubmit.bind(this),
                };
                const adyenForm = this._getAdyenForm();
                const checkout = await AdyenCheckout(configuration);
                this.adyenDropin = checkout.create(
                    response.adyenCode, {
                        showStoredPaymentMethods: false,
                        showBrandsUnderCardNumber: false,
                        showPayButton: false,
                        setStatusAutomatically: true,
                        brands: ['mc','visa','amex', 'discover'],
                    },
                ).mount(adyenForm);
                this.adyenDropin.providerId = paymentProviderId;
            });
        }).guardedCatch((error) => {
            error.event.preventDefault();
            this._displayErrorDialog(
                _t("Server Error"),
                _t("An error occurred when displayed this payment form."),
                error.message.data.message,
            );
        });
    },
    /**
     *
     * @returns {Element | null} the component to mount adyen inline form
     * @private
     */
    _getAdyenForm(){
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(radio);
        return inlineForm?.querySelector('[name="o_adyen_dropin_container"]')
    },

    /**
     * Trigger the payment processing by submitting the drop-in.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the payment option's provider
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the transaction
     * @return {void}
     */
    _initiatePaymentFlow(provider, paymentOptionId, paymentMethodCode, flow) {
        if (provider !== 'adyen' || flow === 'token') {
            this._super(...arguments); // Tokens are handled by the generic flow
            return;
        }
        if (this.adyenDropin === undefined) { // The drop-in has not been properly instantiated
            this._displayErrorDialog(
                _t("Server Error"), _t("We are not able to process your payment.")
            );
        } else {
            this.adyenDropin.submit();
        }
    },
        /**
     * Handle the additional details event of the Adyen drop-in.
     *
     * @private
     * @param {object} state - The state of the drop-in
     * @param {object} dropin - The drop-in
     * @return {void}
     */
    _dropinOnAdditionalDetails: function (state, dropin) {
        return this._rpc({
            route: '/payment/adyen/payment_details',
            params: {
                'provider_id': dropin.providerId,
                'reference': this.adyenDropin.reference,
                'payment_details': state.data,
            },
        }).then(paymentDetails => {
            if (paymentDetails.action) { // Additional action required from the shopper
                dropin.handleAction(paymentDetails.action);
            } else { // The payment reached a final state, redirect to the status page
                window.location = '/payment/status';
            }
        }).guardedCatch((error) => {
            error.event.preventDefault();
            this._displayErrorDialog(
                _t("Server Error"),
                _t("We are not able to process your payment."),
                error.message.data.message,
            );
        });
    },

    /**
     * Handle the error event of the Adyen drop-in.
     *
     * @private
     * @param {object} error - The error in the drop-in
     * @return {void}
     */
    _dropinOnError: function (error) {
        if (!this.$('div[name="o_payment_error"]')) { // Don't replace a specific server error.
            this._displayErrorDialog(
                _t("Incorrect Payment Details"),
                _t("Please verify your payment details."),
            );
        }
        else {
            this._enableButton();
        }
    },

    /**
     * Handle the submit event of the Adyen drop-in and initiate the payment.
     *
     * @private
     * @param {object} state - The state of the drop-in
     * @param {object} dropin - The drop-in
     * @return {void}
     */
    _dropinOnSubmit: function (state, dropin) {
        // Create the transaction and retrieve the processing values
        return this._rpc({
            route: this.txContext.transactionRoute,
            params: this._prepareTransactionRouteParams('adyen', dropin.providerId, 'direct'),
        }).then(processingValues => {
            this.adyenDropin.reference = processingValues.reference; // Store final reference
            // Initiate the payment
            return this._rpc({
                route: '/payment/adyen/payments',
                params: {
                    'provider_id': dropin.providerId,
                    'reference': processingValues.reference,
                    'converted_amount': processingValues.converted_amount,
                    'currency_id': processingValues.currency_id,
                    'partner_id': processingValues.partner_id,
                    'payment_method': state.data.paymentMethod,
                    'access_token': processingValues.access_token,
                    'browser_info': state.data.browserInfo,
                },
            });
        }).then(paymentResponse => {
            if (paymentResponse.action) { // Additional action required from the shopper
                this._hideInputs(); // Only the inputs of the inline form should be used
                $('body').unblock(); // The page is blocked at this point, unblock it
                dropin.handleAction(paymentResponse.action);
            } else { // The payment reached a final state, redirect to the status page
                window.location = '/payment/status';
            }
        }).guardedCatch((error) => {
            error.event.preventDefault();
            this._displayErrorDialog(
                _t("Server Error"),
                _t("We are not able to process your payment."),
                error.message.data.message,
            );
        });
    },

};

paymentForm.include(adyenMixin);
