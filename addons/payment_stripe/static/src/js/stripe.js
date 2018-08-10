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

    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }
    function getStripeHandler()
    {
        var handler = StripeCheckout.configure({
            key: $("input[name='stripe_key']").val(),
            image: $("input[name='stripe_image']").val(),
            locale: 'auto',
            token: function(token, args) {
                handler.isTokenGenerate = true;
                if ($.blockUI) {
                    var msg = _t("Just one more second, confirming your payment...");
                    $.blockUI({
                        'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                                '    <br />' + msg +
                                '</h2>'
                    });
                }
                ajax.jsonRpc("/payment/stripe/create_charge", 'call', {
                    tokenid: token.id,  // TBE TODO: for backward compatibility, remove on master
                    email: token.email, // TBE TODO: for backward compatibility, remove on master
                    token: token,
                    amount: $("input[name='amount']").val(),
                    acquirer_id: $("#acquirer_stripe").val(),
                    currency: $("input[name='currency']").val(),
                    invoice_num: $("input[name='invoice_num']").val(),
                    tx_ref: $("input[name='invoice_num']").val(),
                    return_url: $("input[name='return_url']").val()
                }).always(function(){
                    if ($.blockUI) {
                        $.unblockUI();
                    }
                }).done(function(data){
                    handler.isTokenGenerate = false;
                    window.location.href = data;
                }).fail(function(data){
                    var msg = data && data.data && data.data.message;
                    var wizard = $(qweb.render('stripe.error', {'msg': msg || _t('Payment error')}));
                    wizard.appendTo($('body')).modal({'keyboard': true});
                });
            },
        });
        return handler;
    }

    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
    }

    var observer = new MutationObserver(function(mutations, observer) {
        for(var i=0; i<mutations.length; ++i) {
            for(var j=0; j<mutations[i].addedNodes.length; ++j) {
                if(mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') == 'stripe') {
                    display_stripe_form($(mutations[i].addedNodes[j]));
                }
            }
        }
    });


    function display_stripe_form(provider_form) {
        // Open Checkout with further options
        var payment_form = $('.o_payment_form');
        if(!payment_form.find('i').length)
            payment_form.append('<i class="fa fa-spinner fa-spin"/>');
            payment_form.attr('disabled','disabled');

        var payment_tx_url = payment_form.find('input[name="prepare_tx_url"]').val();
        var access_token = $("input[name='access_token']").val() || $("input[name='token']").val() || '';

        var get_input_value = function(name) {
            return provider_form.find('input[name="' + name + '"]').val();
        }

        var acquirer_id = parseInt(provider_form.find('#acquirer_stripe').val());
        var amount = parseFloat(get_input_value("amount") || '0.0');
        var currency = get_input_value("currency");
        var email = get_input_value("email");
        var invoice_num = get_input_value("invoice_num");
        var merchant = get_input_value("merchant");

        ajax.jsonRpc(payment_tx_url, 'call', {
            acquirer_id: acquirer_id,
            access_token: access_token,
        }).then(function(data) {
            var $pay_stripe = $('#pay_stripe').detach();
            try { provider_form[0].innerHTML = data; } catch (e) {}
            // Restore 'Pay Now' button HTML since data might have changed it.
            $(provider_form[0]).find('#pay_stripe').replaceWith($pay_stripe);
        }).done(function () {
            getStripeHandler().open({
                name: merchant,
                description: invoice_num,
                email: email,
                currency: currency,
                amount: _.contains(int_currencies, currency) ? amount : amount * 100,
            });
        });
    }

    $.getScript("https://checkout.stripe.com/checkout.js", function(data, textStatus, jqxhr) {
        observer.observe(document.body, {childList: true});
        display_stripe_form($('form[provider="stripe"]'));
    });
});
