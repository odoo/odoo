odoo.define('payment_stripe.stripe_form', function(require) {
"use strict";

var payment = require('payment.payment_form');

payment.include({

    init: function(parent, options) {
        this._super.apply(this, arguments);
        if ($('.o_payment_form').find('input[type="radio"]:checked').length && $('.o_payment_form').find('input[type="radio"]:checked').data().provider == 'stripe') {
            $('.o_payment_form').find('.stripe_payment_type').removeClass('d-none');
        }
    },

    radioClickEvent: function (ev) {
        this._super.apply(this, arguments);
        if (ev.currentTarget.dataset.provider == 'stripe') {
            this.$el.find('.stripe_payment_type').removeClass('d-none');
        } else {
            this.$el.find('.stripe_payment_type').addClass('d-none');
        }
    },

});

});
