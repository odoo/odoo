/* global AdyenCheckout */
odoo.define('payment_adyen.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    const adyenMixin = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Handle the additional details event of the Adyen drop-in.
         *
         * @private
         * @param {object} state - The state of the drop-in
         * @param {object} dropin - The drop-in
         * @return {Promise}
         */
        _dropinOnAdditionalDetails: function (state, dropin) {
            this._hideInputs(); // Only the inputs of the inline form should be used
            return this._rpc({
                route: '/payment/adyen/payment_details',
                params: {
                    'acquirer_id': dropin.acquirerId,
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
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });
        },

        /**
         * Handle the error event of the Adyen drop-in.
         *
         * @private
         * @param {object} error - The error in the drop-in
         * @return {undefined}
         */
        _dropinOnError: function (error) {
            this._displayError(
                _t("Incorrect Payment Details"),
                _t("Please verify your payment details.")
            );
        },

        /**
         * Handle the submit event of the Adyen drop-in and initiate the payment.
         *
         * @private
         * @param {object} state - The state of the drop-in
         * @param {object} dropin - The drop-in
         * @return {Promise}
         */
        _dropinOnSubmit: function (state, dropin) {
            // Create the transaction and retrieve the processing values
            return this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams('adyen', dropin.acquirerId, 'direct'),
            }).then(processingValues => {
                this.adyenDropin.reference = processingValues.reference; // Store final reference
                // Initiate the payment
                return this._rpc({
                    route: '/payment/adyen/payments',
                    params: {
                        'acquirer_id': dropin.acquirerId,
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
                    dropin.handleAction(paymentResponse.action);
                } else { // The payment reached a final state, redirect to the status page
                    window.location = '/payment/status';
                }
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });
        },

        /**
         * Prepare the inline form of Adyen for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'adyen') {
                return this._super(...arguments);
            }

            // Check if instantiation of the drop-in is needed
            if (flow === 'token') {
                return Promise.resolve(); // No drop-in for tokens
            } else if (this.adyenDropin && this.adyenDropin.acquirerId === paymentOptionId) {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
                return Promise.resolve(); // Don't re-instantiate if already done for this acquirer
            }

            // Overwrite the flow of the select payment option
            this._setPaymentFlow('direct');

            // Get public information on the acquirer (state, client_key)
            return this._rpc({
                route: '/payment/adyen/acquirer_info',
                params: {
                    'acquirer_id': paymentOptionId,
                },
            }).then(acquirerInfo => {
                // Get the available payment methods
                return this._rpc({
                    route: '/payment/adyen/payment_methods',
                    params: {
                        'acquirer_id': paymentOptionId,
                        'partner_id': parseInt(this.txContext.partnerId),
                        'amount': this.txContext.amount
                            ? parseFloat(this.txContext.amount)
                            : undefined,
                        'currency_id': this.txContext.currencyId
                            ? parseInt(this.txContext.currencyId)
                            : undefined,
                    },
                }).then(paymentMethodsResult => {
                    // Instantiate the drop-in
                    const configuration = {
                        paymentMethodsResponse: paymentMethodsResult,
                        clientKey: acquirerInfo.client_key,
                        locale: (this._getContext().lang || 'en-US').replace('_', '-'),
                        environment: acquirerInfo.state === 'enabled' ? 'live' : 'test',
                        onAdditionalDetails: this._dropinOnAdditionalDetails.bind(this),
                        onError: this._dropinOnError.bind(this),
                        onSubmit: this._dropinOnSubmit.bind(this),
                    };
                    const checkout = new AdyenCheckout(configuration);
                    this.adyenDropin = checkout.create(
                        'dropin', {
                            openFirstPaymentMethod: true,
                            openFirstStoredPaymentMethod: false,
                            showStoredPaymentMethods: false,
                            showPaymentMethods: true,
                            showPayButton: false,
                            setStatusAutomatically: true,
                        },
                    ).mount(`#o_adyen_dropin_container_${paymentOptionId}`);
                    this.adyenDropin.acquirerId = paymentOptionId;
                });
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occurred when displayed this payment form."),
                    error.message.data.message
                );
            });
        },

        /**
         * Trigger the payment processing by submitting the drop-in.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        async _processPayment(provider, paymentOptionId, flow) {
            if (provider !== 'adyen' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }
            if (this.adyenDropin === undefined) { // The drop-in has not been properly instantiated
                this._displayError(
                    _t("Server Error"), _t("We are not able to process your payment.")
                );
            } else {
                return await this.adyenDropin.submit();
            }
        },

    };

    checkoutForm.include(adyenMixin);
    manageForm.include(adyenMixin);
});
