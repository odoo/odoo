odoo.define('payment_test.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    const paymentTestMixin = {
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Create and process the transaction.
         *
         * For an acquirer to define its own transaction processing flow, to do pre-processing work
         * or to do post-processing work, it must override this method.
         *
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {undefined}
         */
        _processPayment: function (provider, paymentOptionId, flow) {.
//        arj todo: override prepare ... voir dans sale comment c'est fait et rajouter ce dont j'ai besoin/
//          j'aurais les params que je get
            const prom = this._super(...arguments);
            prom.then(result => {
                if (provider === 'test' && flow === 'direct') {
                    const orderId = this.txContext.orderId ? parseInt(this.txContext.orderId) : undefined;
                    const currencyId = this.txContext.currencyId ? parseInt(this.txContext.currencyId) : null;
                    const partnerId = this.txContext.partnerId ? parseInt(this.txContext.partnerId) : undefined;
                    const amount = this.txContext.amount !== undefined ? parseFloat(this.txContext.amount) : null;
                    const $checkedRadios = this.$('input[type="radio"]:checked');
                    const checkedRadio = $checkedRadios[0];
                    const acquirerId = this._getPaymentOptionIdFromRadio(checkedRadio);
                    // Normal acquirer don't have access to these information.
                    const ccNumber = document.getElementById('cc_number').value;
                    const ccHolderName = document.getElementById('cc_holder_name').value;
                    const ccExpiry = document.getElementById('cc_expiry').value;
                    const ccCvc = document.getElementById('cc_cvc').value;
                    // we simulate a feedback from our imaginary acquirer API
                    this._rpc({
                         route: '/payment/test/payments',
                         params: {
                             'acquirer_id': provider,
                             'reference': result.reference,
                             'partner_id': partnerId,
                             'amount': amount,
                             'currency_id': currencyId,
                             'cc_number': ccNumber,
                             'cc_name': ccHolderName,
                             'cc_expiry': ccExpiry,
                             'cc_cvc': ccCvc,
                         },
                    }).then(result => {
                        window.location = '/payment/status';
                    });
                }
                return result;
            });

        },


        /**
         * Prepare the inline form of Test for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {undefined}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'test') {
                return this._super(...arguments);
            }
            this._setPaymentFlow('direct');
        },
    }

    checkoutForm.include(paymentTestMixin);
    manageForm.include(paymentTestMixin);
});
