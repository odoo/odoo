/** @odoo-module */
/* global Stripe */

import { _t } from '@web/core/l10n/translation';
import { StripeOptions } from '@payment_stripe/js/stripe_options';

export default {

    /**
     * Prepare the inline form of Stripe for direct payment.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    _prepareInlineForm(code, paymentOptionId, flow) {
        if (code !== 'stripe') {
            this._super(...arguments);
            return;
        }

        // Check if instantiation of the element is needed.
        if (flow === 'token') {
            return; // No elements for tokens.
        } else if (this.stripeElements && this.stripeElements.providerId === paymentOptionId) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation.
            return; // Don't re-instantiate if already done for this provider.
        }

        // Overwrite the flow of the select payment option.
        this._setPaymentFlow('direct');

        // Extract and deserialize the inline form values.
        const stripeInlineForm = document.getElementById(
            `o_stripe_${this.formType}_element_container_${paymentOptionId}`
        );
        this.stripeInlineFormValues = JSON.parse(stripeInlineForm.dataset['inlineFormValues']);

        // Instantiate the payment element.
        this.stripeJS = Stripe(
            this.stripeInlineFormValues['publishable_key'],
            // The values required by Stripe Connect are inserted into the dataset.
            new StripeOptions()._prepareStripeOptions(stripeInlineForm.dataset),
        );
        this.stripeElements = this.stripeJS.elements(this._getElementsOptions());
        this.stripeElements.providerId = paymentOptionId;
        const paymentElementOptions = {
            defaultValues: {
                billingDetails: this.stripeInlineFormValues['billingDetails'],
            },
            layout: {
                type: 'accordion',
                defaultCollapsed: false,
                radios: false,
                spacedAccordionItems: true,
            },
        };
        const paymentElement = this.stripeElements.create('payment', paymentElementOptions);
        paymentElement.mount(stripeInlineForm);

        const tokenizationCheckbox = document.getElementById(
            `o_payment_provider_inline_${this.formType}_form_${paymentOptionId}`
        ).querySelector('input[name="o_payment_save_as_token"]');
        if (this.formType === 'checkout' && tokenizationCheckbox) {
            // Disable the tokenization checkbox for non-compatible payment methods.
            paymentElement.addEventListener('change', ev => {
                this.selectedPaymentMethod = ev.value.type;
                if (this.stripeInlineFormValues['payment_methods_tokenization_support']
                    [this.selectedPaymentMethod]) {
                    tokenizationCheckbox.disabled = false;
                    tokenizationCheckbox.removeAttribute('title');
                } else {
                    tokenizationCheckbox.disabled = true;
                    tokenizationCheckbox.checked = false;
                    tokenizationCheckbox.title = _t("The selected payment method cannot be saved.");
                }
            });
            // Display tokenization-specific inputs when the tokenization checkbox is checked.
            tokenizationCheckbox.addEventListener('input', () => {
                this.stripeElements.update({
                    setupFutureUsage: tokenizationCheckbox.checked ? 'off_session' : null,
                });
            });
        }
    },

    /**
     * Prepare the required options for the configuration of the Elements object.
     *
     * @private
     * @return {Object}
     */
    _getElementsOptions() {
        return {
            appearance: { theme: 'stripe' },
            currency: this.stripeInlineFormValues['currency_name'],
            captureMethod: this.stripeInlineFormValues['capture_method'],
        };
    },

    /**
     * Trigger the form validation by submitting the payment element.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the payment option's provider.
     * @param {number} paymentOptionId - The id of the payment option handling the transaction.
     * @param {string} flow - The online payment flow of the transaction.
     * @return {void}
     */
    async _processPayment(provider, paymentOptionId, flow) {
        if (provider !== 'stripe' || flow === 'token') {
            await this._super(...arguments); // Tokens are handled by the generic flow.
            return;
        }
        if (this.stripeElements === undefined) { // Elements has not been properly instantiated.
            this._displayError(
                _t("Server Error"), _t("We are not able to process your payment.")
            );
        } else {
            // Trigger form validation and wallet collection.
            const _super = this._super.bind(this);
            const { error: submitError } = await this.stripeElements.submit();
            if (submitError) {
                this._displayError(
                    _t("Incorrect Payment Details"),
                    _t("Please verify your payment details."),
                );
            } else { // There is no invalid input, resume the generic flow.
                return await _super(...arguments);
            }
        }
    },

    /**
     * Process the payment.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the provider
     * @param {number} providerId - The id of the provider handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {void}
     */
    async _processDirectPayment(code, providerId, processingValues) {
        if (code !== 'stripe') {
            await this._super(...arguments);
            return;
        }

        const { error } = await this._stripeConfirmIntent(processingValues);
        if (error) {
            this._displayError(
                _t("Server Error"),
                _t("We are not able to process your payment."),
                error.message,
            );
        }
    },

    /**
     * Confirm the intent on Stripe's side and handle any next action.
     *
     * @private
     * @param {object} processingValues - The processing values of the transaction.
     * @return {object} The processing error, if any.
     */
    async _stripeConfirmIntent(processingValues) {},

};
