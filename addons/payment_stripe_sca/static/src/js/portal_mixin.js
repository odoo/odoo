odoo.define('payment_stripe_sca.website_mixin', function (require) {
    "use strict";

var ajax = require('web.ajax');
var core = require('web.core');

var _t = core._t;

return {
    makePayment: function(ev) {
        return this._super.apply(this, arguments);
    },
    postProcessTx: function(data, acquirer_id) {
        var self = this;
        var _super = this._super;
        this._isStripeAcquirer(acquirer_id).then(function(result){
            if (result) {
                var stripe_data = $(data).serializeArray();
                return self._redirectToStripeCheckout(stripe_data);
            } else {
                return _super(data, acquirer_id);
            }
        })
    },
    _isStripeAcquirer: function(acquirer_id) {
        return ajax.jsonRpc('/payment/get_provider', 'call', {acquirer_id: acquirer_id}).then(function(result) {
            return result === 'stripe';
        });
    },
    _redirectToStripeCheckout: function(stripe_data) {
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
        var stripe_key = _.where(stripe_data, {name: 'stripe_key'})[0].value;
        var stripe = Stripe(stripe_key);
    
        stripe.redirectToCheckout({
            sessionId: _.where(stripe_data, {name: 'session_id'})[0].value,
        }).then(function (result) {
            if (result.error) {
                displayError(result.error.message);
            }
        });
    },
    disableButton: function (button) {
        $(button).attr('disabled', true);
        $(button).children('.fa-lock').removeClass('fa-lock');
        $(button).prepend('<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>');
    },
};
});
