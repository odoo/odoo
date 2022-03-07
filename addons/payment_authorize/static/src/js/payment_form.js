/* global Accept */
odoo.define('payment_authorize.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const ajax = require('web.ajax');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    const authorizeMixin = {

        /**
         * Return all relevant inline form inputs based on the payment method type of the acquirer.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {Object} - An object mapping the name of inline form inputs to their DOM element
         */
        _getInlineFormInputs: function (acquirerId) {
            if (this.authorizeInfo.payment_method_type === "credit_card") {
                return {
                    card: document.getElementById(`o_authorize_card_${acquirerId}`),
                    month: document.getElementById(`o_authorize_month_${acquirerId}`),
                    year: document.getElementById(`o_authorize_year_${acquirerId}`),
                    code: document.getElementById(`o_authorize_code_${acquirerId}`),
                };
            } else {
                return {
                    accountName: document.getElementById(`o_authorize_account_name_${acquirerId}`),
                    accountNumber: document.getElementById(
                        `o_authorize_account_number_${acquirerId}`
                    ),
                    abaNumber: document.getElementById(`o_authorize_aba_number_${acquirerId}`),
                    accountType: document.getElementById(`o_authorize_account_type_${acquirerId}`),
                };
            }
        },

        /**
         * Return the credit card or bank data to pass to the Accept.dispatch request.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {Object} - Data to pass to the Accept.dispatch request
         */
        _getPaymentDetails: function (acquirerId) {
            const inputs = this._getInlineFormInputs(acquirerId);
            if (this.authorizeInfo.payment_method_type === 'credit_card') {
                return {
                    cardData: {
                        cardNumber: inputs.card.value.replace(/ /g, ''), // Remove all spaces
                        month: inputs.month.value,
                        year: inputs.year.value,
                        cardCode: inputs.code.value,
                    },
                };
            } else {
                return {
                    bankData: {
                        nameOnAccount: inputs.accountName.value.substring(0, 22), // Max allowed by acceptjs
                        accountNumber: inputs.accountNumber.value,
                        routingNumber: inputs.abaNumber.value,
                        accountType: inputs.accountType.value,
                    },
                };
            }
        },

        /**
         * Prepare the inline form of Authorize.Net for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'authorize') {
                return this._super(...arguments);
            }

            if (flow === 'token') {
                return Promise.resolve(); // Don't show the form for tokens
            }

            this._setPaymentFlow('direct');

            let acceptJSUrl = 'https://js.authorize.net/v1/Accept.js';
            return this._rpc({
                route: '/payment/authorize/get_acquirer_info',
                params: {
                    'acquirer_id': paymentOptionId,
                },
            }).then(acquirerInfo => {
                if (acquirerInfo.state !== 'enabled') {
                    acceptJSUrl = 'https://jstest.authorize.net/v1/Accept.js';
                }
                this.authorizeInfo = acquirerInfo;
            }).then(() => {
                ajax.loadJS(acceptJSUrl);
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
         * Dispatch the secure data to Authorize.Net.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        _processPayment: function (provider, paymentOptionId, flow) {
            if (provider !== 'authorize' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }

            if (!this._validateFormInputs(paymentOptionId)) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve();
            }

            // Build the authentication and card data objects to be dispatched to Authorized.Net
            const secureData = {
                authData: {
                    apiLoginID: this.authorizeInfo.login_id,
                    clientKey: this.authorizeInfo.client_key,
                },
                ...this._getPaymentDetails(paymentOptionId),
            };

            // Dispatch secure data to Authorize.Net to get a payment nonce in return
            return Accept.dispatchData(
                secureData, response => this._responseHandler(paymentOptionId, response)
            );
        },

        /**
         * Handle the response from Authorize.Net and initiate the payment.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @param {object} response - The payment nonce returned by Authorized.Net
         * @return {Promise}
         */
        _responseHandler: function (acquirerId, response) {
            if (response.messages.resultCode === 'Error') {
                let error = "";
                response.messages.message.forEach(msg => error += `${msg.code}: ${msg.text}\n`);
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error
                );
                return Promise.resolve();
            }

            // Create the transaction and retrieve the processing values
            return this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams('authorize', acquirerId, 'direct'),
            }).then(processingValues => {
                // Initiate the payment
                return this._rpc({
                    route: '/payment/authorize/payment',
                    params: {
                        'reference': processingValues.reference,
                        'partner_id': processingValues.partner_id,
                        'opaque_data': response.opaqueData,
                        'access_token': processingValues.access_token,
                    }
                }).then(() => window.location = '/payment/status');
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
         * Checks that all payment inputs adhere to the DOM validation constraints.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {boolean} - Whether all elements pass the validation constraints
         */
        _validateFormInputs: function (acquirerId) {
            const inputs = Object.values(this._getInlineFormInputs(acquirerId));
            return inputs.every(element => element.reportValidity());
        },

    };

    checkoutForm.include(authorizeMixin);
    manageForm.include(authorizeMixin);
});
