/* global Stripe */

import { StripeOptions } from '@payment_stripe/interactions/stripe_options';
import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    setup() {
        super.setup();
        this.stripeElements = {}; // Store the element of each instantiated payment method.
    },

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
            await super._prepareInlineForm(...arguments);
            return;
        }

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

        // Resolve the Stripe payment method type for this payment method code.
        const stripePmType = (
            this.stripeInlineFormValues['payment_methods_mapping'][paymentMethodCode]
            ?? paymentMethodCode
        );

        // ACSS Debit does not support Stripe's deferred intent flow (Elements `mode` option).
        // For ACSS, Elements must be initialized with a real `clientSecret` from a pre-created
        // PaymentIntent. We defer this initialization to _processDirectFlow where the
        // client_secret is available from processingValues, and skip element mounting here.
        if (stripePmType === 'acss_debit') {
            // Store the container reference so we can mount the element later in _processDirectFlow.
            this._acssStripeInlineForm = stripeInlineForm;
            this._acssPaymentOptionId = paymentOptionId;
            return;
        }

        // Instantiate the elements.
        let elementsOptions =  {
            appearance: { theme: 'stripe' },
            currency: this.stripeInlineFormValues['currency_name'],
            captureMethod: this.stripeInlineFormValues['capture_method'],
            paymentMethodTypes: [stripePmType],
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
            // Tokens are handled by the generic flow.
            await super._initiatePaymentFlow(...arguments);
            return;
        }

        // For ACSS debit, elements are mounted later in _processDirectFlow after the
        // client_secret is available, so skip the submit step here.
        const stripePmType = (
            this.stripeInlineFormValues?.['payment_methods_mapping']?.[paymentMethodCode]
            ?? paymentMethodCode
        );
        if (stripePmType !== 'acss_debit') {
            // Trigger form validation and wallet collection.
            try {
                await this.waitFor(this.stripeElements[paymentOptionId].submit());
            } catch (error) {
                this._displayErrorDialog(_t("Incorrect payment details"), error.message);
                this._enableButton();
                return;
            }
        }

        await super._initiatePaymentFlow(...arguments);
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
            await super._processDirectFlow(...arguments);
            return;
        }

        // For ACSS debit, the Elements instance could not be created during _prepareInlineForm
        // because acss_debit does not support the deferred intent flow (mode: 'payment').
        // Now that we have a real client_secret from the pre-created PaymentIntent, we
        // initialize Elements with it and mount the payment element before confirming.
        const stripePmType = (
            this.stripeInlineFormValues?.['payment_methods_mapping']?.[paymentMethodCode]
            ?? paymentMethodCode
        );
        if (stripePmType === 'acss_debit') {
            const clientSecret = processingValues['client_secret'];
            this.stripeElements[paymentOptionId] = this.stripeJS.elements({
                appearance: { theme: 'stripe' },
                clientSecret: clientSecret,
            });
            const paymentElement = this.stripeElements[paymentOptionId].create('payment', {
                defaultValues: {
                    billingDetails: this.stripeInlineFormValues['billing_details'],
                },
            });
            paymentElement.on('loaderror', response => {
                this._displayErrorDialog(
                    _t("Cannot display the payment form"), response.error.message
                );
            });
            // Mount into the container stored during _prepareInlineForm.
            paymentElement.mount(this._acssStripeInlineForm);

            // Wait for the element to be fully ready before submitting.
            await new Promise((resolve) => paymentElement.on('ready', resolve));

            // Submit the element to validate bank account details entered by the customer.
            try {
                await this.waitFor(this.stripeElements[paymentOptionId].submit());
            } catch (error) {
                this._displayErrorDialog(_t("Incorrect payment details"), error.message);
                this._enableButton();
                return;
            }
        }

        const { error } = await this.waitFor(
            this._stripeConfirmIntent(processingValues, paymentOptionId)
        );
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
