odoo.define('payment_adyen.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const { loadJS, loadCSS } = require('@web/core/assets');
    const { pyToJsLocale } = require('@web/core/l10n/utils');
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
         * @param {object} actions - The possible action handlers to call
         * @return {Promise}
         */
        _dropinOnAdditionalDetails: function (state, dropin, actions) {
            return this._rpc({
                route: '/payment/adyen/payment_details',
                params: {
                    'provider_id': dropin.providerId,
                    'reference': this.adyenDropin.reference,
                    'payment_details': state.data,
                },
            }).then(paymentResponse => {
                if (!paymentResponse.resultCode) {
                    actions.reject();
                    return;
                }
                actions.resolve(paymentResponse)
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
        * Called when the payment is completed or failed.
        *
        * @private
        * @param {object} state
        * @param {object} dropin
        * @return {void}
        */
        _dropinOnPaymentResolved: function (state, dropin) {
            window.location = '/payment/status';
        },

        /**
         * Handle the error event of the Adyen drop-in.
         *
         * @private
         * @param {object} error - The error in the drop-in
         * @return {undefined}
         */
        _dropinOnError: function (error='') {
            this._displayError(
                _t("Incorrect Payment Details"),
                _t("Please verify your payment details."),
            );
        },

        /**
         * Handle the submit event of the Adyen drop-in and initiate the payment.
         *
         * @private
         * @param {object} state - The state of the drop-in
         * @param {object} dropin - The drop-in
         * @param {object} actions - The possible action handlers to call
         * @return {Promise}
         */
        _dropinOnSubmit: function (state, dropin, actions) {
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
                if (!paymentResponse.resultCode) {
                    actions.reject();
                    return;
                }
                if (paymentResponse.action && paymentResponse.action.type !== 'redirect') {
                    this._hideInputs(); // Only the inputs of the inline form should be used
                    $('body').unblock(); // The page is blocked at this point, unblock it
                }
                actions.resolve(paymentResponse)
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
         * @param {string} code - The code of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (code, paymentOptionId, flow) {
            if (code !== 'adyen') {
                return this._super(...arguments);
            }

            // Check if instantiation of the drop-in is needed
            if (flow === 'token') {
                return Promise.resolve(); // No drop-in for tokens
            } else if (this.adyenDropin && this.adyenDropin.providerId === paymentOptionId) {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
                return Promise.resolve(); // Don't re-instantiate if already done for this provider
            }

            // Overwrite the flow of the select payment option
            this._setPaymentFlow('direct');

            // Get public information on the provider (state, client_key)
            return this._rpc({
                route: '/payment/adyen/provider_info',
                params: {
                    'provider_id': paymentOptionId,
                },
            }).then(providerInfo => {
                // Get the available payment methods
                return this._rpc({
                    route: '/payment/adyen/payment_methods',
                    params: {
                        'provider_id': paymentOptionId,
                        'partner_id': parseInt(this.txContext.partnerId),
                        'amount': this.txContext.amount
                            ? parseFloat(this.txContext.amount)
                            : undefined,
                        'currency_id': this.txContext.currencyId
                            ? parseInt(this.txContext.currencyId)
                            : undefined,
                    },
                }).then(async (paymentMethodsResult) => {
                    // Instantiate the drop-in
                    const configuration = {
                        paymentMethodsResponse: paymentMethodsResult['payment_methods_data'],
                        amount: paymentMethodsResult['amount_formatted'],
                        clientKey: providerInfo.client_key,
                        locale: pyToJsLocale(this._getContext().lang || 'en-US'),
                        countryCode: paymentMethodsResult['country_code'],
                        environment: providerInfo.state === 'enabled' ? 'live' : 'test',
                        showPayButton: false,
                        onAdditionalDetails: this._dropinOnAdditionalDetails.bind(this),
                        onPaymentCompleted: this._dropinOnPaymentResolved.bind(this),
                        onPaymentFailed: this._dropinOnPaymentResolved.bind(this),
                        onError: this._dropinOnError.bind(this),
                        onSubmit: this._dropinOnSubmit.bind(this),
                    };

                    const script = this.el.parentElement.querySelector(
                        'script[src="https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/4.7.3/adyen.js"]'
                    );
                    if (script) script.remove();
                    const link = this.el.parentElement.querySelector(
                        'link[href="https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/4.7.3/adyen.css"]'
                    );
                    if (link) link.remove();
                    await loadJS('https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.9.0/adyen.js');
                    await loadCSS('https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.9.0/adyen.css');

                    const { AdyenCheckout, Dropin } = window.AdyenWeb;
                    AdyenCheckout(configuration)
                        .then(checkout => {
                            this.adyenDropin = new Dropin(checkout, {
                                paymentMethodsConfiguration: {
                                    card: {
                                        hasHolderName: true,
                                        holderNameRequired: true,
                                    },
                                    paypal: {
                                        blockPayPalCreditButton: true,
                                        blockPayPalPayLaterButton: true,
                                        showPayButton: true,
                                        style: {
                                            disableMaxWidth: true
                                        },
                                    },
                                },
                                openFirstStoredPaymentMethod: false,
                                showStoredPaymentMethods: false,
                                disableFinalAnimation: true,
                                onSelect: component => {
                                    if (component.props.name === "PayPal") {
                                        this.txContext.tokenizationRequested = false;
                                        // Hide Pay button
                                        this._hideInputs();
                                    }
                                    else {
                                        this._showInputs();
                                    }
                                }
                            });
                            this.adyenDropin.mount(`#o_adyen_dropin_container_${paymentOptionId}`);
                            this.adyenDropin.providerId = paymentOptionId;
                        });
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occurred when displayed this payment form."),
                    error.message.data.message
                );
            });
    })},

        /**
         * Trigger the payment processing by submitting the drop-in.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's provider
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
                await this.adyenDropin.submit();
                if (!this.adyenDropin.isValid) {
                    this._dropinOnError();
                }
            }
        },

    };

    checkoutForm.include(adyenMixin);
    manageForm.include(adyenMixin);
});
