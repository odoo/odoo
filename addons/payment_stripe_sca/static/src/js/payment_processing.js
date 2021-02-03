odoo.define('payment_stripe_sca.processing', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var rpc = require('web.rpc')
    var PaymentProcessing = require('payment.processing');

    return PaymentProcessing.include({
        init: function () {
            this._super.apply(this, arguments);
            this._authInProgress = false;
        },
        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                return ajax.loadJS("https://js.stripe.com/v3/");
            })
        },
        _stripeAuthenticate: function (tx) {
            var stripe = Stripe(tx.stripe_publishable_key);
            return $.Deferred(function(defer) {
                stripe.handleCardPayment(tx.stripe_payment_intent_secret)
                    .then(function(result) {defer.resolve(result)})
            }).then(function(result) {
                return rpc.query({
                    route: '/payment/stripe/s2s/process_payment_intent',
                    params: _.extend({}, result.paymentIntent, {reference: tx.reference, error: result.error}),
                });
            }).then(function(result) {
                window.location = '/payment/process';
            }).fail(function (error) {
                this._authInProgress = false;
            });
        },
        processPolledData: function(transactions) {
            this._super.apply(this, arguments);
            for (var itx=0; itx < transactions.length; itx++) {
                var tx = transactions[itx];
                if (tx.acquirer_provider === 'stripe' && tx.state === 'pending' && tx.stripe_payment_intent_secret && !this._authInProgress) {
                    this._authInProgress = true;
                    this._stripeAuthenticate(tx);
                }
            }
        },
    });
});