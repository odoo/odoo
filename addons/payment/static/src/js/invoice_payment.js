odoo.define('payment.payment_transaction', function (require) {
 'use strict';
    var ajax = require('web.ajax');
    var InvoicePayment = require('payment.payment_method');

    $(document).ready(function () {
        if($("#online_invoice_payment").length){
            var invoice_payment = new InvoicePayment();
            invoice_payment.attachTo($("#online_invoice_payment"));
        }
    });
});
 