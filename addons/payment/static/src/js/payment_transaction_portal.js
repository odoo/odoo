odoo.define('payment.website_payment', function (require) {
"use strict";

require('web.dom_ready');
var ajax = require('web.ajax');

    if (!$('.o_website_payment').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_website_payment'");
    }

    // When clicking on payment button: create the tx using json then continue to the acquirer
    var $payment = $(".o_website_payment_form");
    $payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        $(ev.currentTarget).attr('disabled', true);
        $(ev.currentTarget).prepend('<i class="fa fa-refresh fa-spin"></i> ');
        var $form = $(ev.currentTarget).parents('form');
        var data =$("div[class~='o_website_payment_new_payment']").data();
        ajax.jsonRpc('/website_payment/transaction/', 'call', data).then(function (result) {
            $form.submit();
        });
    });
});
