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
            var sale_order_id = $("input[name='return_url']").val().match(/quote\/([0-9]+)/);
            if (sale_order_id) {
                sale_order_id = parseInt(sale_order_id[1]);
            }

            handler.isTokenGenerate = true;
            ajax.jsonRpc("/payment/stripe/create_charge", 'call', {
                tokenid: token.id,
                email: token.email,
                amount: $("input[name='amount']").val(),
                acquirer_id: $("#acquirer_stripe").val(),
                currency: $("input[name='currency']").val(),
                invoice_num: $("input[name='invoice_num']").val(),
                return_url: $("input[name='return_url']").val(),
                sale_order_id: sale_order_id,
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
        var acquirer_id = $(e.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
        if (! acquirer_id) {
            return false;
        }

        ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {}).then(function (data) {
            $form.html(data);
            handler.open({
                name: $("input[name='merchant']").val(),
                description: $("input[name='invoice_num']").val(),
                currency: $("input[name='currency']").val(),
                amount: $("input[name='amount']").val()*100
            });
            e.preventDefault();
        });

    });
});
