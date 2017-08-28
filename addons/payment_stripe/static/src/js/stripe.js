odoo.define('payment_stripe.stripe', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    var qweb = core.qweb;
    ajax.loadXML('/payment_stripe/static/src/xml/stripe_templates.xml', qweb);

    // The following currencies are integer only, see
    // https://stripe.com/docs/currencies#zero-decimal
    var int_currencies = [
        'BIF', 'XAF', 'XPF', 'CLP', 'KMF', 'DJF', 'GNF', 'JPY', 'MGA', 'PYG',
        'RWF', 'KRW', 'VUV', 'VND', 'XOF'
    ];

    var handler = StripeCheckout.configure({
        key: $("input[name='stripe_key']").val(),
        image: $("input[name='stripe_image']").val(),
        locale: 'auto',
        token: function(token, args) {
            handler.isTokenGenerate = true;
            ajax.jsonRpc("/payment/stripe/create_charge", 'call', {
                tokenid: token.id,
                email: token.email,
                amount: $("input[name='amount']").val(),
                acquirer_id: $("#acquirer_stripe").val(),
                currency: $("input[name='currency']").val(),
                invoice_num: $("input[name='invoice_num']").val(),
                return_url: $("input[name='return_url']").val()
            }).done(function(data){
                handler.isTokenGenerate = false;
                window.location.href = data;
            }).fail(function(){
                var msg = arguments && arguments[1] && arguments[1].data && arguments[1].data.message;
                var wizard = $(qweb.render('stripe.error', {'msg': msg || _t('Payment error')}));
                wizard.appendTo($('body')).modal({'keyboard': true});
            });
        },
    });

    $(document).ready(function (){
        if (!$('.o_payment_form').length) {
            return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
        }

        $('#o_payment_form_pay').on('click', function(ev){
            // we retrieve the payment form
            var parent_form = ev.target.form;
            // then the checked radio
            var checked_radio = $('input[type="radio"]:checked', parent_form);
            // check if there's one checked radio
            if(checked_radio.length != 1) {
                return;
            }
            // if there's a checked radio, we retrieve the usefull data
            var acquirer_id = checked_radio.data('acquirerId');
            var provider = checked_radio.data('provider');
            var is_form_payment = checked_radio.data('form-payment') === "True";
            // now we check if the user has clicked on stripe radio button and wants to pay via the checkout form
            if(provider != "stripe" || is_form_payment !== true) {
                return;
            }
            // from here we retrieve the inputs that contains the data we need
            var provider_form = $("#o_payment_form_acq_" + acquirer_id, parent_form);

            var access_token = $('input[name="token"]', provider_form).val();
            var so_id = $("input[name='return_url']", provider_form).val().match(/quote\/([0-9]+)/) || undefined;
            if (so_id) {
                so_id = parseInt(so_id[1]);
            }

            if ($('.o_website_payment').length !== 0) {
                var currency = $("input[name='currency']", provider_form).val();
                var amount = parseFloat($("input[name='amount']", provider_form).val() || '0.0');
                if (!_.contains(int_currencies, currency)) {
                    amount = amount*100;
                }

                ajax.jsonRpc('/website_payment/transaction', 'call', {
                        reference: $("input[name='invoice_num']", provider_form).val(),
                        amount: amount,
                        currency_id: currency,
                        acquirer_id: acquirer_id
                    })
                    handler.open({
                        name: $("input[name='merchant']", provider_form).val(),
                        description: $("input[name='invoice_num']", provider_form).val(),
                        currency: currency,
                        amount: amount,
                    });
            } else {
                var currency = $("input[name='currency']", provider_form).val();
                var amount = parseFloat($("input[name='amount']", provider_form).val() || '0.0');
                if (!_.contains(int_currencies, currency)) {
                    amount = amount*100;
                }

                // TBE TODO: Pass 'so_id: so_id' and 'access_token: access_token' on the URL
                ajax.jsonRpc('/shop/payment/transaction/', 'call', {
                        acquirer_id: acquirer_id
                    }, {'async': false}).then(function (data) {
                    try {
                        provider_form.html(data);
                    }
                    catch(err) { } // here it will catch an error saying that payment_stripe.stripe is already started
                    handler.open({
                        name: $("input[name='merchant']", provider_form).val(),
                        description: $("input[name='invoice_num']", provider_form).val(),
                        currency: currency,
                        amount: amount,
                    });
                });
            }
        });
    });
});
