/** @odoo-module */
/* global Stripe */

import { _t } from '@web/core/l10n/translation';
import { StripeOptions } from '@payment_stripe/js/stripe_options';
import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Stripe for direct payment.
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
        if (providerCode !== 'stripe') {
            this._super(...arguments);
            return;
        }

        // Check if instantiation of the element is needed.
        this.stripeElements ??= {}; // Store the element of each instantiated payment method.
        // Check if instantiation of the element is needed.
        if (flow === 'token') {
            return; // No elements for tokens.
        } else if (this.stripeElements[paymentOptionId]) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation.
            return; // Don't re-instantiate if already done for this provider.
        }

        // Overwrite the flow of the select payment option.
        this._setPaymentFlow('direct');

        // Extract and deserialize the inline form values.
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(radio);
        const stripeInlineForm = inlineForm.querySelector('[name="o_stripe_element_container"]');
        this.stripeInlineFormValues = JSON.parse(
            stripeInlineForm.dataset['stripeInlineFormValues']
        );

        // Instantiate Stripe object if needed.
        this.stripeJS ??= Stripe(
            this.stripeInlineFormValues['publishable_key'],
            // The values required by Stripe Connect are inserted into the dataset.
            new StripeOptions()._prepareStripeOptions(stripeInlineForm.dataset),
        );

        // Instantiate the elements.
        let elementsOptions =  {
            appearance: { theme: 'stripe' },
            currency: this.stripeInlineFormValues['currency_name'],
            captureMethod: this.stripeInlineFormValues['capture_method'],
            paymentMethodTypes: [
                this.stripeInlineFormValues['payment_methods_mapping'][paymentMethodCode]
                ?? paymentMethodCode
            ],
        };
        if (this.paymentContext['mode'] === 'payment') {
            elementsOptions.mode = 'payment';
            elementsOptions.amount = parseInt(this.stripeInlineFormValues['minor_amount']);
            if (this.stripeInlineFormValues['is_tokenization_required']) {
                elementsOptions.setupFutureUsage = 'off_session';
            }
        }
        else {
            elementsOptions.mode = 'setup';
            elementsOptions.setupFutureUsage = 'off_session';
        }
        this.stripeElements[paymentOptionId] = this.stripeJS.elements(elementsOptions);

        // Instantiate the payment element.
        const paymentElementOptions = {
            defaultValues: {
                billingDetails: this.stripeInlineFormValues['billing_details'],
            },
        };
        const paymentElement = this.stripeElements[paymentOptionId].create(
            'payment', paymentElementOptions
        );
        paymentElement.on('loaderror', response => {
            this._displayErrorDialog(_t("Cannot display the payment form"), response.error.message);
        });
        paymentElement.mount(stripeInlineForm);

        const tokenizationCheckbox = inlineForm.querySelector(
            'input[name="o_payment_tokenize_checkbox"]'
        );
        if (tokenizationCheckbox) {
            // Display tokenization-specific inputs when the tokenization checkbox is checked.
            this.stripeElements[paymentOptionId].update({
                setupFutureUsage: tokenizationCheckbox.checked ? 'off_session' : null,
            }); // Force sync the states of the API and the checkbox in case they were inconsistent.
            tokenizationCheckbox.addEventListener('input', () => {
                this.stripeElements[paymentOptionId].update({
                    setupFutureUsage: tokenizationCheckbox.checked ? 'off_session' : null,
                });
            });
        }
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Trigger the payment processing by submitting the elements.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'stripe' || flow === 'token') {
            await this._super(...arguments); // Tokens are handled by the generic flow.
            return;
        }

        // Trigger form validation and wallet collection.
        const _super = this._super.bind(this);
        try {
            await this.stripeElements[paymentOptionId].submit();
        } catch (error) {
            this._displayErrorDialog(_t("Incorrect payment details"), error.message);
            this._enableButton();
            return
        }
        return await _super(...arguments);
    },

    /**
     * Process Stripe implementation of the direct payment flow.
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
        if (providerCode !== 'stripe') {
            await this._super(...arguments);
            return;
        }

        const { error } = await this._stripeConfirmIntent(processingValues, paymentOptionId);
        if (error) {
            this._displayErrorDialog(_t("Payment processing failed"), error.message);
            this._enableButton();
        }
    },

    /**
     * Confirm the intent on Stripe's side and handle any next action.
     *
     * @private
     * @param {object} processingValues - The processing values of the transaction.
     * @param {number} paymentOptionId - The id of the payment option handling the transaction.
     * @return {object} The processing error, if any.
     */
    async _stripeConfirmIntent(processingValues, paymentOptionId) {
        const confirmOptions = {
            elements: this.stripeElements[paymentOptionId],
            clientSecret: processingValues['client_secret'],
            confirmParams: {
                return_url: processingValues['return_url'],
            },
        };
        if (this.paymentContext['mode'] === 'payment'){
             return await this.stripeJS.confirmPayment(confirmOptions);
        }
        else {
            return await this.stripeJS.confirmSetup(confirmOptions);
        }
    },

});
