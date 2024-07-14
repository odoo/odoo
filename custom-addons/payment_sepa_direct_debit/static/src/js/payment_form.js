/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { RPCError } from "@web/core/network/rpc_service";

import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of SEPA for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The custom mode of the selected payment option's provider. The
     *                                provider code is replaced in the payment form to allow
     *                                comparing custom modes.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {void}
     */
    _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'sepa_direct_debit') {
            this._super(...arguments);
            return;
        } else if (flow === 'token') {
            return; // Don't show the form for tokens.
        }
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Verify the validity of the IBAN input before trying to process a payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {string} providerCode - The custom mode of the selected payment option's provider. The
     *                                provider code is replaced in the payment form to allow
     *                                comparing custom modes.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'sepa_direct_debit' || flow === 'token') {
            this._super(...arguments); // Tokens are handled by the generic flow.
            return;
        }

        const ibanInput = this._getIbanInput();

        if (!ibanInput.reportValidity()) {
            this._enableButton();
            return; // Let the browser request to fill out required fields
        }

        this._super(...arguments);
    },

    /**
     * Link the IBAN to the transaction as an inactive mandate.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    _processDirectFlow (providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'sepa_direct_debit') {
            this._super(...arguments);
            return;
        }

        // Assign the SDD mandate corresponding to the IBAN to the transaction.
        const ibanInput = this._getIbanInput();
        this.rpc('/payment/sepa_direct_debit/set_mandate', {
            'reference': processingValues.reference,
            'iban': ibanInput.value,
            'access_token': processingValues.access_token,
        }).then(() => {
            window.location = '/payment/status';
        }).catch((error) => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(
                    _t("Payment processing failed"),
                    error.data.message,
                );
            } else {
                return Promise.reject(error);
            }
        });
    },

    // #=== GETTERS ===#

    /**
     * Return the IBAN input.
     *
     * @private
     * @return {HTMLInputElement}
     */
    _getIbanInput() {
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(radio);
        return inlineForm?.querySelector('#o_sdd_iban');
    },

});
