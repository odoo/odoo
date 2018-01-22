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
        'BIF', 'XAF', 'XPF', 'CLP', 'KMF', 'DJF', 'GNF', 'JPY', 'MGA', 'PYGí',
        'RWF', 'KRW', 'VUV', 'VND', 'XOF'
    ];

    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }

    var handler = StripeCheckout.configure({
        key: $("input[name='stripe_key']").val(),
        image: $("input[name='stripe_image']").val(),
        locale: 'auto',
        closed: function() {
          if (!handler.isTokenGenerate) {
                $('#pay_stripe')
                    .removeAttr('disabled')
                    .find('i').remove();
          }
        },
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
            }).fail(function(){
                var msg = arguments && arguments[1] && arguments[1].data && arguments[1].data.arguments && arguments[1].data.arguments[0];
                var wizard = $(qweb.render('stripe.error', {'msg': msg || _t('Payment error')}));
                wizard.appendTo($('body')).modal({'keyboard': true});
            });
        },
    });

    $('#pay_stripe').on('click', function(e) {
        // Open Checkout with further options
        if(!$(this).find('i').length)
            $(this).append('<i class="fa fa-spinner fa-spin"/>');
            $(this).attr('disabled','disabled');

        var $form = $(e.currentTarget).parents('form');
        var acquirer_id = $(e.currentTarget).closest('div.oe_sale_acquirer_button,div.oe_quote_acquirer_button,div.o_website_payment_new_payment');
        acquirer_id = acquirer_id.data('id') || acquirer_id.data('acquirer_id');
        if (! acquirer_id) {
            return false;
        }

        var so_token = $("input[name='token']").val() || '';
        var so_id = $("input[name='return_url']").val().match(/quote\/([0-9]+)/) || undefined;
        if (so_id) {
            so_id = parseInt(so_id[1]);
        }

        e.preventDefault();

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
            var url = _.str.sprintf("/quote/%s/transaction/%s/%s", so_id, acquirer_id, so_token);
            var create_tx = ajax.jsonRpc(url, 'call', {}).then(function (data) {
                try { $form.html(data); } catch (e) {};
            });
        }
        else {
            var create_tx = ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {
                    so_id: so_id,
                    so_token: so_token
            }).then(function (data) {
                try { $form.html(data); } catch (e) {};
            });
        }
        create_tx.done(function () {
            if (!_.contains(int_currencies, currency)) {
                amount = amount*100;
            }
            handler.open({
                name: $("input[name='merchant']").val(),
                description: $("input[name='invoice_num']").val(),
                email: $("input[name='email']").val(),
                currency: currency,
                amount: amount,
            });
        });
    });
});
