import { loadJS, loadCSS } from '@web/core/assets';
import { _t } from '@web/core/l10n/translation';
import { pyToJsLocale } from '@web/core/l10n/utils';
import { rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    setup() {
        super.setup();
        this.adyenCheckout = undefined;
        this.adyenComponents = {}; // Store the component of each instantiated payment method.
    },

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
            await super._prepareInlineForm(...arguments);
            return;
        }

        // Check if instantiation of the component is needed.
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

        this.el.parentElement.querySelector(
            'script[src="https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/5.39.0/adyen.js"]'
        )?.remove();
        this.el.parentElement.querySelector(
            'link[href="https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/5.39.0/adyen.css"]'
        )?.remove();
        await this.waitFor(
            loadJS('https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.9.0/adyen.js')
        );
        await this.waitFor(
            loadCSS('https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.9.0/adyen.css')
        );
        const { AdyenCheckout, createComponent } = window.AdyenWeb;

        // Create the checkout object if not already done for another payment method.
        if (!this.adyenCheckout) {
            try {
                // Await the RPC to let it create AdyenCheckout before using it.
                const response = await this.waitFor(rpc(
                    '/payment/adyen/payment_methods',
                    {
                        'provider_id': providerId,
                        'partner_id': parseInt(this.paymentContext['partnerId']),
                        'formatted_amount': formattedAmount,
                    },
                ));
                // Create the Adyen Checkout SDK.
                const providerState = this._getProviderState(radio);
                const configuration = {
                    paymentMethodsResponse: response,
                    clientKey: inlineFormValues['client_key'],
                    amount: formattedAmount,
                    locale: pyToJsLocale(document.documentElement.getAttribute('lang')) || 'en-US',
                    countryCode: response['country_code'],
                    environment: providerState === 'enabled' ? 'live' : 'test',
                    onAdditionalDetails: this._adyenOnSubmitAdditionalDetails.bind(this),
                    onPaymentCompleted: this._adyenOnPaymentResolved.bind(this),
                    onPaymentFailed: this._adyenOnPaymentResolved.bind(this),
                    onError: this._adyenOnError.bind(this),
                    onSubmit: this._adyenOnSubmit.bind(this),
                };
                this.adyenCheckout = await this.waitFor(AdyenCheckout(configuration));
            } catch (error) {
                if (error instanceof RPCError) {
                    this._displayErrorDialog(
                        _t("Cannot display the payment form"), error.data.message
                    );
                    this._enableButton();
                    return;
                }
                else {
                    return Promise.reject(error);
                }
            }
        }

        // Instantiate and mount the component.
        const componentConfiguration = {
            showPayButton: false,
        };
        if (paymentMethodCode === 'card') {
            componentConfiguration['hasHolderName'] = true;
            componentConfiguration['holderNameRequired'] = true;
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
            // Define necessary fields as the step submitForm is missed.
            Object.assign(this.paymentContext, {
                tokenizationRequested: false,
                providerId: providerId,
                paymentMethodId: paymentOptionId,
            });
        }
        const inlineForm = this._getInlineForm(radio);
        const adyenContainer = inlineForm.querySelector('[name="o_adyen_component_container"]');
        this.adyenComponents[paymentOptionId] = createComponent(
            inlineFormValues['adyen_pm_code'],
            this.adyenCheckout,
            componentConfiguration
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
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'adyen' || flow === 'token') {
            // Tokens are handled by the generic flow
            await super._initiatePaymentFlow(...arguments);
            return;
        }

        if (!this.adyenComponents[paymentOptionId]) {  // Component creation failed.
            this._enableButton();
            return;
        }

        this.adyenComponents[paymentOptionId].submit();

        // The `onError` event handler is not used to validate inputs anymore since v5.0.0.
        if (!this.adyenComponents[paymentOptionId].isValid) {
            this._displayErrorDialog(_t("Incorrect payment details"));
            this._enableButton();
        }
    },

    /**
     * Handle the submit event of the component and initiate the payment.
     *
     * @private
     * @param {object} state - The state of the component.
     * @param {object} component - The component.
     * @param {object} actions - The possible action handlers to call.
     * @return {void}
     */
    async _adyenOnSubmit(state, component, actions) {
        try {
            // Create the transaction and retrieve the processing values.
            const processingValues = await this.waitFor(rpc(
                this.paymentContext['transactionRoute'],
                this._prepareTransactionRouteParams(),
            ));
            component.reference = processingValues.reference; // Store final reference.
            // Initiate the payment.
            const paymentResponse = await this.waitFor(rpc('/payment/adyen/payments', {
                'provider_id': processingValues.provider_id,
                'reference': processingValues.reference,
                'converted_amount': processingValues.converted_amount,
                'currency_id': processingValues.currency_id,
                'partner_id': processingValues.partner_id,
                'payment_method': state.data.paymentMethod,
                'access_token': processingValues.access_token,
                'browser_info': state.data.browserInfo,
            }));
            if (!paymentResponse.resultCode) {
                actions.reject();
                return;
            }
            if (paymentResponse.action && paymentResponse.action.type !== 'redirect') {
                this._hideInputs(); // Only the inputs of the inline form should be used.
                 // The page is blocked at this point; unblock it.
                this.env.bus.trigger('ui', 'unblock');
            }
            actions.resolve(paymentResponse);
        } catch (error) {
            const error_message = error instanceof RPCError ? error.data.message : error.message;
            this._displayErrorDialog(_t("Payment processing failed"), error_message);
            this._enableButton();
        }
    },

    /**
     * Handle the additional details event of the component.
     *
     * @private
     * @param {object} state - The state of the component.
     * @param {object} component - The component.
     * @param {object} actions - The possible action handlers to call.
     * @return {void}
     */
    async _adyenOnSubmitAdditionalDetails(state, component, actions) {
        try {
            const paymentDetails = await this.waitFor(rpc('/payment/adyen/payments/details', {
                'provider_id': this.paymentContext['providerId'],
                'reference': component.reference,
                'payment_details': state.data,
            }));
            if (!paymentDetails.resultCode) {
                actions.reject();
                return;
            }
            actions.resolve(paymentDetails);
        } catch (error) {
            const error_message = error instanceof RPCError ? error.data.message : error.message;
            this._displayErrorDialog(_t("Payment processing failed"), error_message);
            this._enableButton();
        }
    },

    /**
    * Called when the payment is completed or failed.
    *
    * @private
    * @param {object} result
    * @param {object} component
    * @return {void}
    */
    _adyenOnPaymentResolved(result, component) {
        window.location = '/payment/status';
    },

    /**
     * Handle the error event of the component.
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
