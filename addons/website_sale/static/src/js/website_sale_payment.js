odoo.define('website_sale.payment', function (require) {
"use strict";

var WebsiteSalePayment = require('payment.transaction');

$(document).ready(function () {
    // If option is enable
    if($("#website_sale_payment").length){
        var website_sale_payment = new WebsiteSalePayment();
        website_sale_payment.attachTo($("#website_sale_payment"));
    }

    if ($("#checkbox_cgv").length) {
      $("#checkbox_cgv").click(function() {
        $("div.o_payment_acquirer_button").find('input, button').prop("disabled", !this.checked);
      });
    }
});

});
