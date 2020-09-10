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
         * @return {undefined}
         */
        _dropinOnAdditionalDetails: function (state, dropin) {
            this._rpc({
                route: '/payment/adyen/payment_details',
                params: {
                    'acquirer_id': dropin.acquirerId,
                    'reference': this.adyenDropin.reference,
                    'details': state.data.details,
                    'payment_data': state.data.paymentData,
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
         * @param {object} _error - The error in the drop-in
         * @return {undefined}
         */
        _dropinOnError: function (_error) {
            this._displayError(
                _t("Incorrect Payment Details"),
                _t("Please verify your payment details.")
            );
        },

        /**
         * Handle the submit event of the Adyen drop-in.
         *
         * @private
         * @param {object} state - The state of the drop-in
         * @param {object} dropin - The drop-in
         * @return {undefined}
         */
        _dropinOnSubmit: function (state, dropin) {
            // Call the init route to initialize the transaction and retrieve processing values
            this._rpc({
                route: this.txContext.initTxRoute,
                params: {
                    'payment_option_id': dropin.acquirerId,
                    'reference': this.txContext.reference,
                    'amount': this.txContext.amount !== undefined
                        ? parseFloat(this.txContext.amount) : null,
                    'currency_id': this.txContext.currencyId
                        ? parseInt(this.txContext.currencyId) : null,
                    'partner_id': this.txContext.partnerId
                        ? parseInt(this.txContext.partnerId) : undefined,
                    'order_id': this.txContext.orderId
                        ? parseInt(this.txContext.orderId) : undefined,
                    'flow': 'direct',
                    'tokenization_requested': this.txContext.tokenizationRequested,
                    'is_validation': this.txContext.isValidation !== undefined
                        ? this.txContext.isValidation : false,
                    'landing_route': this.txContext.landingRoute,
                    'access_token': this.txContext.accessToken
                        ? this.txContext.accessToken : undefined,
                    'csrf_token': core.csrf_token,
                },
            }).then(processingValues => {
                this.adyenDropin.reference = processingValues.reference; // Store final reference
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
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {undefined}
         */
        _prepareInlineForm: function (paymentOptionId, provider, flow) {
            if (provider !== 'adyen') {
                return this._super(...arguments);
            }

            // Check if instantiation of the drop-in is needed
            if (
                this.adyenDropin
                && this.adyenDropin.acquirerId === paymentOptionId
                && flow !== 'token'
            ) {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
                return; // Don't re-instantiate if already done for this acquirer
            } else if (flow === 'token') {
                return; // No drop-in for tokens
            }

            // Overwrite the flow of the select payment option
            this._setPaymentFlow('direct');

            // Get the available payment methods
            this._rpc({
                route: '/payment/adyen/payment_methods',
                params: {
                    'acquirer_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                    'amount': this.txContext.amount ? parseFloat(this.txContext.amount) : undefined,
                    'currency_id': this.txContext.currencyId
                        ? parseInt(this.txContext.currencyId)
                        : undefined,
                },
            }).then(paymentMethodsResult => {
                // Generate the origin key
                this._rpc({
                    route: '/payment/adyen/origin_key',
                    params: {
                        'acquirer_id': paymentOptionId,
                    },
                }).then(originKeyResult => {
                    // Extract the origin key from the returned object
                    const originKeyResultKeys = Object.keys(originKeyResult.originKeys);
                    const originKey = originKeyResult.originKeys[originKeyResultKeys[0]];

                    // Instantiate the drop-in
                    const configuration = {
                        paymentMethodsResponse: paymentMethodsResult,
                        originKey: originKey,
                        locale: (this._getContext().lang || 'en-US').replace('_', '-'),
                        environment: 'test', // TODO ANV change to 'live'
                        openFirstPaymentMethod: true,
                        openFirstStoredPaymentMethod: false,
                        showStoredPaymentMethods: false,
                        showPaymentMethods: true,
                        showPayButton: false,
                        onAdditionalDetails: this._dropinOnAdditionalDetails.bind(this),
                        onError: this._dropinOnError.bind(this),
                        onSubmit: this._dropinOnSubmit.bind(this),
                    };
                    const checkout = new AdyenCheckout(configuration);
                    this.adyenDropin = checkout.create('dropin').mount(
                        `#adyen-dropin-container_${paymentOptionId}`
                    );
                    this.adyenDropin.acquirerId = paymentOptionId;
                });
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occured when displayed this payment form."),
                    error.message.data.message
                );
            });
        },

        /**
         * Submit the drop-in.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {string} flow - The online payment flow of the transaction
         * @return {undefined}
         */
        _processTx: function (paymentOptionId, provider, flow) {
            if (provider !== 'adyen') {
                return this._super(...arguments);
            }

            // Process the payment accordingly to the flow
            if (flow === 'direct') {
                this.adyenDropin.submit();
            } else if (flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }
        },

    };

    checkoutForm.include(adyenMixin);
    manageForm.include(adyenMixin);
});
