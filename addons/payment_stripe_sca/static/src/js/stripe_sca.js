odoo.define('payment_stripe_sca.stripe_sca', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;
var _t = core._t;


if ($.blockUI) {
    // our message needs to appear above the modal dialog
    $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
    $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
}

if(!$('#pay_stripe').length) {
    return $.Deferred().reject("DOM doesn't contain '#pay_stripe'");
}

function displayError(message) {
    var wizard = $(qweb.render('stripe.error', {'msg': message || _t('Payment error')}));
    wizard.appendTo($('body')).modal({'keyboard': true});
    if ($.blockUI) {
        $.unblockUI();
    }
    $("#o_payment_form_pay").removeAttr('disabled');
}


function _redirectToStripeCheckout() {
    // Open Checkout with further options
    if ($.blockUI) {
        var msg = _t("Just one more second, we are redirecting you to Stripe...");
        $.blockUI({
            'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                    '    <br />' + msg +
                    '</h2>'
        });
    }

    var paymentForm = $('.o_payment_form');
    if (!paymentForm.find('i').length) {
        paymentForm.append('<i class="fa fa-spinner fa-spin"/>');
        paymentForm.attr('disabled', 'disabled');
    }

    var stripe = Stripe($("input[name='stripe_key']").val());

    stripe.redirectToCheckout({
        sessionId: $("input[name='session_id']").val()
    }).then(function (result) {
        if (result.error) {
            displayError(result.error.message);
        }
    });
}

$('#pay_stripe').on('click', function(e) {
    e.preventDefault();
    var $form = $(e.currentTarget).parents('form');
    var acquirer = $(e.currentTarget).closest('div.oe_sale_acquirer_button,div.oe_quote_acquirer_button,div.o_website_payment_new_payment');
    var acquirer_id = acquirer.data('id') || acquirer.data('acquirer_id');;

    if (! acquirer_id) {
        return false;
    }
    if ($("input[name='acquirer']:checked").attr('provider') != 'stripe' && $('.js_payment .fa-dot-circle-o').length) {
        var params = {
            tx_type: acquirer.find('input[name="odoo_save_token"]').is(':checked')?'form_save':'form',
            token: acquirer.attr('data-token')
        };
        ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', params).then(function (data) {
            $(data).appendTo('body').submit();
        });
        return false;
    }

    // Open Checkout with further options
    if(!$(this).find('i').length)
        $(this).append('<i class="fa fa-spinner fa-spin"/>');
        $(this).attr('disabled','disabled');

    var so_token = $("input[name='token']").val();
    var so_id = $("input[name='return_url']").val().match(/quote\/([0-9]+)/) || undefined;
    if (so_id) {
        so_id = parseInt(so_id[1]);
    }

    if ($('.o_website_payment').length !== 0) {
        var currency = $("input[name='currency']").val();
        var currency_id = $("input[name='currency_id']").val();
        var amount = parseFloat($("input[name='amount']").val() || '0.0');

        ajax.jsonRpc('/website_payment/transaction', 'call', {
                reference: $("input[name='invoice_num']").val(),
                amount: amount,
                currency_id: currency_id,
                acquirer_id: acquirer_id
            }).then(function () {
                _redirectToStripeCheckout();
            })
    } else {
        var currency = $("input[name='currency']").val();
        var amount = parseFloat($("input[name='amount']").val() || '0.0');

        ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {
                so_id: so_id,
                so_token: so_token,
                return_url: $("input[name='return_url']").val()
            }, {'async': false}).then(function (data) {
            var $pay_stripe = $('#pay_stripe').detach();
            $form.html($(data).find('script[src="/payment_stripe_sca/static/src/js/stripe_sca.js"]').remove().end().html());
            // Restore 'Pay Now' button HTML since data might have changed it.
            $form.find('#pay_stripe').replaceWith($pay_stripe);
            _redirectToStripeCheckout();
        });
    }
});

});
