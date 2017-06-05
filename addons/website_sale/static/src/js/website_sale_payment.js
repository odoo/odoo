odoo.define('website_sale.payment_method', function (require) {
"use strict";

    var ajax = require('web.ajax');
    var WebsiteSalePayment = require('payment.payment_method');

    WebsiteSalePayment.include({
        payment_transaction_action: function(acquirer_id, params){
            // override this function as per controllers(route) of module wise
            if($("#website_sale_payment").length){
                ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', params).then(function (data) {
                    $(data).appendTo('body').submit();
                });
            }
            this._super(acquirer_id, params)
        },
    });

    $(document).ready(function () {

        if($("#website_sale_payment").length){
            var website_sale_payment = new WebsiteSalePayment();
            website_sale_payment.attachTo($("#website_sale_payment"));
        }
        // If option is enable
        if ($("#checkbox_cgv").length) {
            $("#checkbox_cgv").click(function() {
                $("div.o_acquirer_button").find('input, button').prop("disabled", !this.checked);
            });
        }
    });
});
