/** @odoo-module **/
/* global Razorpay */

import { RPCError } from '@web/core/network/rpc_service';
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
            'order_id': processingValues['order_id'],
        };
        const fina = Object.assign({}, processingValues, next);
        const link= "https://eu-test.oppwa.com/v1/paymentWidgets.js?checkoutId=" + fina.order_id;
        this.call('ui', 'unblock');
        this.call("dialog", "add", PaymentHyperpayDialog, {
                order_id: link,
        })

},
});
