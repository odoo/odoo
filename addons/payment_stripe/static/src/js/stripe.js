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
                    tokenid: token.id,
                    email: token.email,
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
                }).fail(function(){
                    var msg = arguments && arguments[1] && arguments[1].data && arguments[1].data.arguments && arguments[1].data.arguments[0];
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

        var acquirer_id = payment_form.find('input[type="radio"][data-provider="stripe"]:checked').data('acquirer-id');
        if (! acquirer_id) {
            return false;
        }

        var access_token = $("input[name='access_token']").val() || $("input[name='token']").val();
        var so_id = $("input[name='return_url']").val().match(/quote\/([0-9]+)/) || undefined;
        if (so_id) {
            so_id = parseInt(so_id[1]);
        }


        var currency = $("input[name='currency']").val();
        var currency_id = $("input[name='currency_id']").val();
        var amount = parseFloat($("input[name='amount']").val() || '0.0');


        if ($('.o_website_payment').length !== 0) {
            var create_tx = ajax.jsonRpc('/website_payment/transaction', 'call', {
                    reference: $("input[name='invoice_num']").val(),
                    amount: amount, // exact amount, not stripe cents
                    currency_id: currency_id,
                    acquirer_id: acquirer_id
            });
        }
        else if ($('.o_website_quote').length !== 0) {
            var url = _.str.sprintf("/quote/%s/transaction/", so_id);
            var create_tx = ajax.jsonRpc(url, 'call', {
                access_token: access_token,
                acquirer_id: acquirer_id
            }).then(function (data) {
                try { provider_form[0].innerHTML = data; } catch (e) {};
            });
        }
        else {
            var create_tx = ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {
                    so_id: so_id,
                    access_token: access_token,
                    acquirer_id: acquirer_id
            }).then(function (data) {
                try { provider_form.innerHTML = data; } catch (e) {};
            });
        }
        create_tx.done(function () {
            if (!_.contains(int_currencies, currency)) {
                amount = amount*100;
            }
            getStripeHandler().open({
                name: $("input[name='merchant']").val(),
                description: $("input[name='invoice_num']").val(),
                email: $("input[name='email']").val(),
                currency: currency,
                amount: amount,
            });
        });
    }

    $.getScript("https://checkout.stripe.com/checkout.js", function(data, textStatus, jqxhr) {
        observer.observe(document.body, {childList: true});
        display_stripe_form($('form[provider="stripe"]'));
    });
});
