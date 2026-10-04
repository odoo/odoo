/* global AbaPayway */

import { loadJS } from '@web/core/assets';
import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';

const ABA_PAYWAY_BASE_URL = 'https://checkout.payway.com.kh';

patch(PaymentForm.prototype, {

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of ABA PayWay for direct payment.
     *
     * @override method from @payment/interactions/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'aba_payway') {
            await super._prepareInlineForm(...arguments);
            return;
        }

        // Overwrite the payment flow of the selected payment method.
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Open the ABA PayWay checkout to process the payment.
     *
     * @override method from @payment/interactions/payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'aba_payway') {
            await super._processDirectFlow(...arguments);
            return;
        }

        await this._loadAbaPaywaySdk();
        AbaPayway.checkout(this._prepareAbaPaywayOptions(processingValues));
    },

    /**
     * Load the ABA PayWay SDK.
     *
     * The `checkout2-0.js` script provided by ABA PayWay only acts as a loader that defers the
     * download of the actual SDK scripts by one second. The SDK scripts are thus loaded directly,
     * in order: `bs.js` injects the DOM elements required to render the checkout, and
     * `checkout.prod.js` defines the `AbaPayway` global. The `n` query parameter of the latter is
     * the cache-buster used by the loader script.
     *
     * @private
     * @return {Promise<void>}
     */
    async _loadAbaPaywaySdk() {
        // Define the global used by the SDK scripts to build their URLs, normally set by the
        // loader script.
        window._aba_checkout_baseUrl ??= ABA_PAYWAY_BASE_URL;

        // `loadJS` returns the same promise for a given URL, so the scripts are executed once.
        await this.waitFor(loadJS(`${ABA_PAYWAY_BASE_URL}/plugins/bs.js`));
        await this.waitFor(loadJS(`${ABA_PAYWAY_BASE_URL}/plugins/checkout.prod.js?n=168`));
    },

    /**
     * Prepare the options to pass to the ABA PayWay checkout.
     *
     * @private
     * @param {object} processingValues - The processing values of the transaction.
     * @return {object} The checkout options.
     */
    _prepareAbaPaywayOptions(processingValues) {
        return {
            'req_time': processingValues['req_time'],
            'merchant_id': processingValues['merchant_id'],
            'tran_id': processingValues['tran_id'],
            'amount': processingValues['amount'],
            'firstname': processingValues['firstname'],
            'lastname': processingValues['lastname'],
            'email': processingValues['email'],
            'phone': processingValues['phone'],
            'type': processingValues['type'],
            'payment_option': processingValues['payment_option'],
            'return_url': processingValues['return_url'],
            'continue_success_url': processingValues['continue_success_url'],
            'currency': processingValues['currency'],
            'lifetime': processingValues['lifetime'],
            'skip_success_page': processingValues['skip_success_page'],
            'payment_gate': processingValues['payment_gate'],
            'form_url': processingValues['form_url'],
            'hash': processingValues['hash'],
        };
    },

});
