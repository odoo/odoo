odoo.define('payment_stripe.stripe', function(require) {
    "use strict";
    var ajax = require('web.ajax');
    var Widget = require('web.Widget');

    var StripePaymentMethod = Widget.extend({
        events: {
            'click #pay_stripe': 'pay_now',
        },

        init: function(){
            this.handler = false;
        },

        start: function() {
            this._super.apply(this, arguments);
            var self = this;
            self.handler = StripeCheckout.configure({
                key: $("input[name='stripe_key']").val(),
                image: $("input[name='stripe_image']").val(),
                locale: 'auto',
                closed: function() {
                  if (!self.handler.isTokenGenerate) {
                        $('#pay_stripe')
                            .removeAttr('disabled')
                            .find('i').remove();
                  }
                },
                token: function(token, args) {
                    self.handler.isTokenGenerate = true;
                    ajax.jsonRpc("/payment/stripe/create_charge", 'call', {
                        tokenid: token.id,
                        email: token.email,
                        amount: $("input[name='amount']").val(),
                        acquirer_id: $("#acquirer_stripe").val(),
                        currency: $("input[name='currency']").val(),
                        invoice_num: $("input[name='invoice_num']").val(),
                        return_url: $("input[name='return_url']").val()
                    }).done(function(data){
                        self.handler.isTokenGenerate = false;
                        window.location.href = data;
                    });
                },
            });
        },

        pay_now: function(event){
            var self = this,
                $currentTarget = $(event.currentTarget),
                $form = $currentTarget.parents('form');

            if(!$currentTarget.find('i').length)
                $currentTarget.append('<i class="fa fa-spinner fa-spin"/>');
                $currentTarget.attr('disabled','disabled');

            var acquirer_id = $currentTarget.closest('div.o_payment_acquirer_button,div.o_website_payment_new_payment');
            acquirer_id = acquirer_id.data('id') || acquirer_id.data('acquirer_id');
            if (! acquirer_id) {
                return false;
            }
            var params = {'form': $form};
            event.preventDefault();
            self.stripe_payment_transaction(acquirer_id, params);
        },

        stripe_payment_transaction: function(acquirer_id, params){
            var self = this,
                handler = self.handler,
                so_token = $("input[name='token']").val(),
                so_id = $("input[name='return_url']").val().match(/quote\/([0-9]+)/) || undefined,
                access_token = $("input[name='access_token']").val(),
                payment_request_id = $("input[name='return_url']").val().match(/payment\/([0-9]+)/) || undefined;
            if (so_id) {
                so_id = parseInt(so_id[1]);
            }
            if (payment_request_id) {
                payment_request_id = parseInt(payment_request_id[1]);
            }
            if ($('#online_invoice_payment').length !== 0){
                ajax.jsonRpc('/payment/transaction/' + acquirer_id, 'call', {
                    payment_request_id: payment_request_id,
                    access_token: access_token
                    }).then(function (data) {
                    params.form.html(data);
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
                    }, {'async': false}).then(function (data) {
                    params.form.html(data);
                    handler.open({
                        name: $("input[name='merchant']").val(),
                        description: $("input[name='invoice_num']").val(),
                        currency: $("input[name='currency']").val(),
                        amount: $("input[name='amount']").val()*100
                    });
                });
            }
        },
    });

    $(document).ready(function () {
        if($("#pay_stripe").length){
            var stripe_payment = new StripePaymentMethod();
            if($("#website_quote_payment").length){
                stripe_payment.attachTo($("#website_quote_payment"));
            }
            if($("#website_sale_payment").length){
                stripe_payment.attachTo($("#website_sale_payment"));
            }
            if($("#online_invoice_payment").length){
                stripe_payment.attachTo($("#online_invoice_payment"));
            }
        }
    });
    return StripePaymentMethod;
});
