odoo.define('payment_stripe.stripe', function(require) {
    "use strict";
    var ajax = require('web.ajax');
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

        var so_token = $("input[name='token']").val();
        var so_id = $("input[name='return_url']").val().match(/quote\/([0-9]+)/) || undefined;
        if (so_id) {
            so_id = parseInt(so_id[1]);
        }

        e.preventDefault();
        if ($('.o_website_payment').length !== 0) {
            ajax.jsonRpc('/website_payment/transaction', 'call', {
                    reference: $("input[name='invoice_num']").val(),
                    amount: $("input[name='amount']").val(),
                    currency_id: $("input[name='currency_id']").val(),
                    acquirer_id: acquirer_id
                }).then(function (data) {
                handler.open({
                    name: $("input[name='merchant']").val(),
                    description: $("input[name='invoice_num']").val(),
                    currency: $("input[name='currency']").val(),
                    amount: $("input[name='amount']").val()*100
                });
            });
        } else {
            ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {
                    so_id: so_id,
                    so_token: so_token
                }).then(function (data) {
                $form.html(data);
                handler.open({
                    name: $("input[name='merchant']").val(),
                    description: $("input[name='invoice_num']").val(),
                    currency: $("input[name='currency']").val(),
                    amount: $("input[name='amount']").val()*100
                });
            });
        }
    });
});
