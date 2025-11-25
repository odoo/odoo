/** @odoo-module */
/* global AbaPayway */

import {patch} from '@web/core/utils/patch';
import {PaymentForm} from '@payment/interactions/payment_form';


patch(PaymentForm.prototype, {

    /**
     * Prepare the inline form of PayWay for direct payment.
     *
     * @override method from @payment/js/payment_form
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

        this._setPaymentFlow('direct');
    },


    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'aba_payway') {
            await super._processDirectFlow(...arguments);
            return;
        }

        // Instantiate ABA PayWay checkout
        const abaPaywayOptions = this._prepareABAPaywayOptions(processingValues);
        AbaPayway.checkout(abaPaywayOptions);
    },

    _prepareABAPaywayOptions(processingValues) {
        return Object.assign({}, {
            'form_url': processingValues['form_url'],
            'tran_id': processingValues['tran_id'],
            'req_time': processingValues['req_time'],
            'lifetime': processingValues['lifetime'],
            'firstname': processingValues['firstname'],
            'lastname': processingValues['lastname'],
            'email': processingValues['email'],
            'phone': processingValues['phone'],
            'type': processingValues['type'],
            'payment_option': processingValues['payment_option'],
            'items': processingValues['items'],
            'amount': processingValues['amount'],
            'payment_gate': processingValues['payment_gate'],
            'merchant_id': processingValues['merchant_id'],
            'currency': processingValues['currency'],
            'custom_fields': processingValues['custom_fields'],
            'skip_success_page': processingValues['skip_success_page'],
            'return_url': processingValues['return_url'],
            'continue_success_url': processingValues['continue_success_url'],
            'hash': processingValues['hash'],
        });
    }
});
