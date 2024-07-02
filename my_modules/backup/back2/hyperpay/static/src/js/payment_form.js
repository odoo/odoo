/** @odoo-module **/
/* global Razorpay */

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import paymentForm from '@payment/js/payment_form';
import { PaymentHyperpayDialog } from './hyperpay_dialog';

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Update the payment context to set the flow to 'direct'.
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

        if (providerCode !== 'hyperpay') {
            this._super(...arguments);
            return;
        }

        if (flow === 'token') {
            return; // No need to update the flow for tokens.
        }

        // Overwrite the flow of the select payment method.
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'hyperpay') {
            this._super(...arguments);
            return;
        }
        const next = {
            'description': processingValues['reference'],
            'key': processingValues['key_id'],
            'test_id': processingValues['customer_id'],
            'customer_id': processingValues['customer_id'],
            'order_id': processingValues['order_id'],
            'recurring': processingValues['is_tokenize_request'] ? '1': '0',
            'handler': response => {
                if (
                    response['hyperpay_payment_id']
                    && response['hyperpay_order_id']
                    && response['hyperpay_signature']
                ) { // The payment reached a final state; redirect to the status page.
                    window.location = '/payment/status';
                }
            },
        };
        const fina = Object.assign({}, processingValues, next);
        console.log(fina)
        const link= "https://eu-test.oppwa.com/v1/paymentWidgets.js?checkoutId=" + fina.order_id;
        this.call('ui', 'unblock');
        this.call("dialog", "add", PaymentHyperpayDialog, {
                order_id: link,
        })

    },
//    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
//
//        if (providerCode !== 'hyperpay') {
//            this._super(...arguments);
//            return;
//        }
//
//        if (flow === 'token') {
//            return; // No need to update the flow for tokens.
//        }
//
//        // Overwrite the flow of the select payment method.
//        this._setPaymentFlow('redirect');
//    },
//
//    // #=== PAYMENT FLOW ===#
//
//    async _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
//        // Create and configure the form element with the content rendered by the server.
//        if (providerCode !== 'hyperpay') {
//            this._super(...arguments);
//            return;
//        }
//        console.log(processingValues);
//        const next = {
//            'description': processingValues['reference'],
//            'key': processingValues['key_id'],
//            'test_id': processingValues['customer_id'],
//            'customer_id': processingValues['customer_id'],
//            'order_id': processingValues['order_id'],
//            'recurring': processingValues['is_tokenize_request'] ? '1': '0',
//            'handler': response => {
//                if (
//                    response['hyperpay_payment_id']
//                    && response['hyperpay_order_id']
//                    && response['hyperpay_signature']
//                ) { // The payment reached a final state; redirect to the status page.
//                    window.location = '/payment/status';
//                }
//            },
//        };
//        const final = Object.assign({}, processingValues, next);
//        console.log(final)
//        const link= "https://eu-test.oppwa.com/v1/paymentWidgets.js?checkoutId=" + final.order_id;
//
//        var dosc = document.getElementById('index');
//
//
//        const div = document.createElement('div');
//        div.innerHTML = processingValues['redirect_form_html'];
//        console.log(div);
////        div.innerHTML = link;
////        const redirectForm = div.querySelector('form');
////        redirectForm.setAttribute('id', 'o_payment_redirect_form');
////        redirectForm.setAttribute('target', '_top');  // Ensures redirections when in an iframe.
//
//        // Submit the form.
////        document.body.appendChild(redirectForm);
////        redirectForm.submit();
//    },

    /**
     * Prepare the options to init the RazorPay SDK Object.
     *
     * @param {object} processingValues - The processing values.
     * @return {object}
     */

});
