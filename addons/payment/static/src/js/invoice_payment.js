odoo.define('payment.payment_transaction', function (require) {
 'use strict';
    var ajax = require('web.ajax');
    var InvoicePayment = require('payment.transaction');

    $(document).ready(function () {
        if($("#online_invoice_payment").length){
            var invoice_payment = new InvoicePayment();
            invoice_payment.attachTo($("#online_invoice_payment"));
        }
        if($(".o_invoice_report_html").length){
            var href = $(location).attr("href"),
                payment_request_id = href.match(/payment\/([0-9]+)/),
                access_token = href.match(/payment\/([^\/?]*)/),
                params = {};

            params.token = access_token ? access_token[1] : '';
            params.payment_request_id = payment_request_id ? payment_request_id[1] : '';
            ajax.jsonRpc('/invoice/report/html/', 'call', params).then(function (data) {
                var $iframe = $('iframe#print_invoice')[0];
                $iframe.contentWindow.document.open('text/htmlreplace');
                $iframe.contentWindow.document.write(data);
            });
        }
        $('a#print_iframe').on('click', function(event){
            event.preventDefault();
            event.stopPropagation();
            $('iframe#print_invoice')[0].contentWindow.print();
        });
    });
});
