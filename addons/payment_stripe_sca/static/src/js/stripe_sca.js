odoo.define('payment_stripe_sca.stripe_sca', function (require) {
"use strict";
if(!$('#pay_stripe').length) {
    return $.Deferred().reject("DOM doesn't contain '#pay_stripe'");
}

var ajax = require('web.ajax');
var core = require('web.core');
var PaymentTransaction = require('website_payment.website_payment');

var qweb = core.qweb;
var _t = core._t;


PaymentTransaction.include({
    _isStripeAcquirer: function() {
        var acq_id = this.$el.data('acquirer_id');
        return ajax.jsonRpc('/payment/get_provider', 'call', {acquirer_id: acq_id}).then(function(result) {
            return result === 'stripe';
        });
    },
    _redirectToStripeCheckout: function() {
        // Open Checkout with further options
        if ($.blockUI) {
            var msg = _t("Just one more second, we are redirecting you to Stripe...");
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
            });
        }
        var button = this.$el.find('button#pay_stripe');
        this.disableButton(button);
        var stripe = Stripe($("input[name='stripe_key']").val());
    
        stripe.redirectToCheckout({
            sessionId: $("input[name='session_id']").val()
        }).then(function (result) {
            if (result.error) {
                displayError(result.error.message);
            }
        });
    },
    onSubmit: function(ev) {
        ev.preventDefault();
        var self = this;
        return this._isStripeAcquirer().then(function(result) {
            if (result) {
                var tx_data = self.getTxData();
                return self.createTransaction(tx_data)
                .then(function (tx_id) {
                    var params = {
                        tx_id: tx_id,
                        stripe_session_id: $("input[name='session_id']").val(),
                    }
                    return ajax.jsonRpc('/payment/stripe/set_payment_intent', 'call', params)
                })
                .then(
                    function() {
                    self._redirectToStripeCheckout()
                });
            } else {
                return self._super();
            }
        });
    }
});


function displayError(message) {
    var wizard = $(qweb.render('stripe.error', {'msg': message || _t('Payment error')}));
    wizard.appendTo($('body')).modal({'keyboard': true});
    if ($.blockUI) {
        $.unblockUI();
    }
    $("#o_payment_form_pay").removeAttr('disabled');
}

return PaymentTransaction;
});
