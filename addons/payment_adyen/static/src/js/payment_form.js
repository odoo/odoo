/** @odoo-module **/
/* global AdyenCheckout */

import { _t } from '@web/core/l10n/translation';
import paymentForm from '@payment/js/payment_form';
import { RPCError } from '@web/core/network/rpc_service';

paymentForm.include({

    adyenCheckout: undefined,
    adyenComponents: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Adyen for direct payment.
     *
     * @override method from payment.payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'adyen') {
            this._super(...arguments);
            return;
        }

        // Check if instantiation of the component is needed.
        this.adyenComponents ??= {}; // Store the component of each instantiated payment method.
        if (flow === 'token') {
            return; // No component for tokens.
        } else if (this.adyenComponents[paymentOptionId]) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation.
            if (paymentMethodCode === 'paypal') { // PayPal uses its own button to submit.
                this._hideInputs();
            }
            return; // Don't re-instantiate if already done for this payment method.
        }

        // Overwrite the flow of the selected payment method.
        this._setPaymentFlow('direct');

        // Extract and deserialize the inline form values.
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineFormValues = JSON.parse(radio.dataset['adyenInlineFormValues']);
        const formattedAmount = inlineFormValues['formatted_amount'];

        // Create the checkout object if not already done for another payment method.
        if (!this.adyenCheckout) {
            await this.rpc('/payment/adyen/payment_methods', { // Await the RPC to let it create AdyenCheckout before using it.
                'provider_id': providerId,
                'partner_id': parseInt(this.paymentContext['partnerId']),
                'formatted_amount': formattedAmount,
            }).then(async response => {
                // Create the Adyen Checkout SDK.
                const providerState = this._getProviderState(radio);
                const configuration = {
                    paymentMethodsResponse: response,
                    clientKey: inlineFormValues['client_key'],
                    amount: formattedAmount,
                    locale: (this._getContext().lang || 'en-US').replace('_', '-'),
                    environment: providerState === 'enabled' ? 'live' : 'test',
                    onAdditionalDetails: this._adyenOnSubmitAdditionalDetails.bind(this),
                    onError: this._adyenOnError.bind(this),
                    onSubmit: this._adyenOnSubmit.bind(this),
                };
                this.adyenCheckout = await AdyenCheckout(configuration);
            }).catch((error) => {
                if (error instanceof RPCError) {
                    this._displayErrorDialog(
                        _t("Cannot display the payment form"), error.data.message
                    );
                    this._enableButton();
                } else {
                    return Promise.reject(error);
                }
            });
        }

        // Instantiate and mount the component.
        const componentConfiguration = {
            showBrandsUnderCardNumber: false,
            showPayButton: false,
            billingAddressRequired: false, // The billing address is included in the request.
        };
        if (paymentMethodCode === 'card') {
            // Forbid Bancontact cards in the card component.
            componentConfiguration['brands'] = ['mc', 'visa', 'amex', 'discover'];
        }
        else if (paymentMethodCode === 'paypal') {
            // PayPal requires the form to be submitted with its own button.
            Object.assign(componentConfiguration, {
                style: {
                    disableMaxWidth: true
                },
                showPayButton: true,
                blockPayPalCreditButton: true,
                blockPayPalPayLaterButton: true
            });
            this._hideInputs();
            // Define necessary fields as the step _submitForm is missed.
            Object.assign(this.paymentContext, {
                tokenizationRequested: false,
                providerId: providerId,
                paymentMethodId: paymentOptionId,
            });
        }
        const inlineForm = this._getInlineForm(radio);
        const adyenContainer = inlineForm.querySelector('[name="o_adyen_component_container"]');
        this.adyenComponents[paymentOptionId] = this.adyenCheckout.create(
            inlineFormValues['adyen_pm_code'], componentConfiguration
        ).mount(adyenContainer);
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Trigger the payment processing by submitting the component.
     *
     * The component is submitted here instead of in `_processDirectFlow` because we use the native
     * submit button for PayPal, which does not follow the standard flow. The transaction is created
     * in `_adyenOnSubmit`.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the payment option handling the transaction.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the transaction.
     * @return {void}
     */
    _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'adyen' || flow === 'token') {
            this._super(...arguments); // Tokens are handled by the generic flow
            return;
        }

        // The `onError` event handler is not used to validate inputs anymore since v5.0.0.
        if (!this.adyenComponents[paymentOptionId].isValid) {
            this._displayErrorDialog(_t("Incorrect payment details"));
            this._enableButton();
            return;
        }
        this.adyenComponents[paymentOptionId].submit();
    },

    /**
     * Handle the submit event of the component and initiate the payment.
     *
     * @private
     * @param {object} state - The state of the component.
     * @param {object} component - The component.
     * @return {void}
     */
    _adyenOnSubmit(state, component) {
        // Create the transaction and retrieve the processing values.
        this.rpc(
            this.paymentContext['transactionRoute'],
            this._prepareTransactionRouteParams(),
        ).then(processingValues => {
            component.reference = processingValues.reference; // Store final reference.
            // Initiate the payment.
            return this.rpc('/payment/adyen/payments', {
                'provider_id': processingValues.provider_id,
                'reference': processingValues.reference,
                'converted_amount': processingValues.converted_amount,
                'currency_id': processingValues.currency_id,
                'partner_id': processingValues.partner_id,
                'payment_method': state.data.paymentMethod,
                'access_token': processingValues.access_token,
                'browser_info': state.data.browserInfo,
            });
        }).then(paymentResponse => {
            if (paymentResponse.action) { // An additional action is required from the shopper.
                this._hideInputs(); // Only the inputs of the inline form should be used.
                this.call('ui', 'unblock'); // The page is blocked at this point, unblock it.
                component.handleAction(paymentResponse.action);
            } else { // The payment reached a final state; redirect to the status page.
                window.location = '/payment/status';
            }
        }).catch((error) => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton();
            } else {
                return Promise.reject(error);
            }
        });
    },

    /**
     * Handle the additional details event of the component.
     *
     * @private
     * @param {object} state - The state of the component.
     * @param {object} component - The component.
     * @return {void}
     */
    _adyenOnSubmitAdditionalDetails(state, component) {
        this.rpc('/payment/adyen/payments/details', {
            'provider_id': this.paymentContext['providerId'],
            'reference': component.reference,
            'payment_details': state.data,
        }).then(paymentDetails => {
            if (paymentDetails.action) { // Additional action required from the shopper.
                component.handleAction(paymentDetails.action);
            } else { // The payment reached a final state; redirect to the status page.
                window.location = '/payment/status';
            }
        }).catch((error) => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton();
            } else {
                return Promise.reject(error);
            }
        });
    },

    /**
     * Handle the error event of the component.
     *
     * See https://docs.adyen.com/online-payments/build-your-integration/?platform=Web
     * &integration=Components&version=5.49.1#handle-the-redirect.
     *
     * @private
     * @param {object} error - The error in the component.
     * @return {void}
     */
    _adyenOnError(error) {
        this._displayErrorDialog(_t("Payment processing failed"), error.message);
        this._enableButton();
    },

});
