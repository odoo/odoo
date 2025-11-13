/* global MercadoPago */

import { _t } from '@web/core/l10n/translation';
import { loadJS } from '@web/core/assets';
import { rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    setup() {
        super.setup();
        this.mercadoPagoBricksBuilder = undefined;
        this.lastMercadoPagoPMId = undefined; // The last instantiated payment method ID.
        this.lastMercadoPagoBrick = undefined; // The brick of the last instantiated payment method.
    },

    // === DOM MANIPULATION === //

    /**
     * Prepare the inline form of Mercado Pago for direct payment.
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
        if (providerCode !== 'mercado_pago' || paymentMethodCode !== 'card') {
            await super._prepareInlineForm(...arguments);
            return;
        }

        // Check if instantiation of the component is needed.
        if (flow === 'token') {
            return; // No component for tokens.
        } else if (paymentOptionId === this.lastMercadoPagoPMId) {
            this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation.
            return; // Don't re-instantiate if already done for this payment method.
        }

        // Extract and deserialize the inline form values.
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineFormValues = JSON.parse(radio.dataset['mercadoPagoInlineFormValues']);

        // Process card payments with the redirect flow if the account is not onboarded with OAuth.
        const publicKey = inlineFormValues['public_key'];
        if (!publicKey) { // The account was not onboarded with OAuth and can't support direct flow.
            return; // Keep the flow to redirect.
        }

        // Overwrite the flow of the selected payment method.
        this._setPaymentFlow('direct');

        // Create the bricksBuilder object if not already done for another payment method.
        if (!this.mercadoPagoBricksBuilder) {
            await this.waitFor(loadJS('https://sdk.mercadopago.com/js/v2'));
            const mercadoPago = new MercadoPago(publicKey, { locale: 'en-US' });
            this.mercadoPagoBricksBuilder = mercadoPago.bricks();
        }

        // Unmount the previous brick, if any, as only one brick can be mounted at a time.
        this.lastMercadoPagoBrick?.unmount();

        // Instantiate and mount the card brick.
        const settings = {
            initialization: {
                amount: this.paymentContext['amount'],
                payer: {
                    email: inlineFormValues['email'],
                },
            },
            customization: {
                visual: {
                    hideFormTitle: true,
                    hidePaymentButton: true,
                },
                paymentMethods: {
                    maxInstallments: 12,
                },
            },
            callbacks: { // Callbacks are required even if empty.
                onReady: () => {},
                onError: () => {},
            },
        };
        this.lastMercadoPagoBrick = await this.waitFor(this.mercadoPagoBricksBuilder.create(
            'cardPayment',
            `o_mercado_pago_brick_container_${providerId}_${paymentOptionId}`,
            settings,
        ));
        this.lastMercadoPagoPMId = paymentOptionId;
    },

        /**
         * Validate the form inputs before initiating the payment flow.
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
        if (providerCode !== 'mercado_pago' || flow !== 'direct') {
            // Tokens and redirect payment methods are handled by the generic flow.
            await super._initiatePaymentFlow(...arguments);
            return;
        }

        // Trigger form validation.
        this.mercadoPagoFormData = await this.waitFor(this.lastMercadoPagoBrick.getFormData());
        if (!this.mercadoPagoFormData){
            this._displayErrorDialog(_t("Incorrect payment details"));
            this._enableButton();  // The submit button is disabled at this point, enable it.
            return;
        }
        await super._initiatePaymentFlow(...arguments);
    },

    /**
     * Process Mercado Pago's implementation of the direct payment flow.
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
        if (providerCode !== 'mercado_pago') {
            super._processDirectFlow(...arguments);
            return;
        }

        try {
            await this.waitFor(rpc('/payment/mercado_pago/payments', {
                'reference': processingValues.reference,
                'transaction_amount': processingValues.amount,
                'token': this.mercadoPagoFormData.token,
                'installments': this.mercadoPagoFormData.installments,
                'payment_method_brand': this.mercadoPagoFormData.payment_method_id,
                'issuer_id': this.mercadoPagoFormData.issuer_id,
            }));
            window.location = '/payment/status';
        } catch(error) {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton();
            } else {
                return Promise.reject(error);
            }
        }
    },

});
